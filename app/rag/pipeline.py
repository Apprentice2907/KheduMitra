import logging
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from app.rag.retriever import get_hybrid_retriever
from app.rag.generator import get_llm

logger = logging.getLogger(__name__)

from app.services.memory_service import memory_service
from app.services.weather_service import weather_service
from app.services.pmkisan_service import pmkisan_service

import os
import random
import asyncio
from app.core.telemetry import log_ab_eval
from app.services.intent_classifier import intent_classifier_service

SYSTEM_PROMPT = """You are KissanBot (KheduMitra), the agricultural assistant for farmers in Gujarat, India.

LANGUAGE RULES — follow strictly:
- If the farmer asks in Gujarati script (ગુજ), respond FULLY in Gujarati script.
- If the farmer asks in Gujarati-English mix (Gu-En), respond in Gujarati-English mix.
- If the farmer asks in Hindi or Hindi-English mix, respond in Hindi.
- If the farmer asks in English, respond in English.
- Never switch languages mid-response.

You have deep knowledge of Gujarat agriculture:
CROPS: groundnut (મગફળી), cotton (કપાસ), castor (દિવેલ), cumin (જીરું), fennel (વરિયાળી),
       sesame (તલ), bajra (બાજ‌), wheat (ઘ‌), onion (ડ‌), banana (કેળ), mango (કેરી)
MANDIS: Rajkot, Junagadh, Amreli, Surat, Ahmedabad, Anand, Bhavnagar, Vadodara, Unjha (Mehsana)
ZONES: Saurashtra (groundnut/cotton), North Gujarat (cumin/fennel), South Gujarat (banana/sugarcane),
       Central Gujarat (tobacco/wheat), Kutch (bajra/sesame)
SCHEMES: iKhedut portal (ikhedut.gujarat.gov.in), PM-KISAN, PMFBY, KCC, Mukhyamantri Kisan Sahay

ALWAYS mention:
- Specific ₹ amounts for schemes and MSP
- Helpline: Gujarat Agriculture Dept 1800-180-1551
- iKhedut portal: ikhedut.gujarat.gov.in (for scheme applications)

Use ONLY the provided context to answer. If the answer is not in context, say:
- Gujarati: "મને આ માહિતી નથી, કૃ‌ 1800-180-1551 ∘ ∘ ∘."
- Hindi: "मुझे इसकी जानकारी नहीं है, कृपया 1800-180-1551 पर कॉल करें।"
- English: "I don't have this information. Please call Gujarat Agriculture Helpline: 1800-180-1551."

Keep answers concise (2-4 sentences) — they will be read aloud on phone.

Detected Intent: {intent}
Farmer Memory — Crop: {crop} | District: {district}
Context: {context}
Question: {question}
Answer:"""

def format_docs(docs):
    return "\n\n".join(doc.page_content for doc in docs)

async def ask_rag(question: str, phone_number: str = None) -> str:
    """
    End-to-end RAG pipeline: retrieves relevant chunks and generates an answer.
    Also fetches conversation memory (crop, district) and runs background extraction.
    """
    # 1. Fire-and-forget memory extraction
    if phone_number:
        memory_service.extract_and_update_memory_async(phone_number, question)
        
    # 2. Retrieve memory for context
    mem = await memory_service.get_farmer_memory(phone_number)
    crop = mem.get("crop", "Unknown")
    district = mem.get("district", "Unknown")
    
    # 3. Intent Classification
    predicted_intent = intent_classifier_service.predict(question)

    retriever = get_hybrid_retriever()
    llm = get_llm()
    
    if not llm:
        logger.error("LLM not initialized (missing GROQ_API_KEY).")
        return "RAG system is currently unconfigured (No LLM)."
        
    prompt = ChatPromptTemplate.from_template(SYSTEM_PROMPT)
    
    # 4. Add PM-KISAN or IMD Weather directly to context if mentioned
    extra_context = ""
    lower_q = question.lower()
    
    # Use predicted intent for robust routing context
    if predicted_intent == "govt_scheme" or "pm kisan" in lower_q or "installment" in lower_q:
        import re
        reg_match = re.search(r'\b(?:[A-Z]{2}\d{7,10}|\d{9,12})\b', question)
        if reg_match:
            status = await pmkisan_service.get_pmkisan_status(reg_match.group(0))
            extra_context += f"\nPM-KISAN Info: {status}\n"
        else:
            if predicted_intent == "govt_scheme":
                extra_context += "\nPM-KISAN Info: If the user is asking about PM-KISAN, please ask for their registration number or Aadhar to check status.\n"
            
    # Gujarat weather keywords: Gujarati script + Hinglish variants
    WEATHER_KEYWORDS = [
        "weather", "mausam", "varshad", "vatar", "barish", "baarish",
        "vrstti", "rain", "rainfall", "forecast", "temperature",
        "\u0ab5\u0ab0\u0ab8\u0abe\u0aa6",  # વ‌ (varshad in Gujarati)
        "\u0aae\u0acc\u0ab8\u0aae",          # ∘ (mausam in Gujarati)
        "\u0ab5\u0abe\u0aa4\u0abe\u0ab5\u0ab0\u0aa3",  # ∘ (environment/weather in Gujarati)
    ]
    if predicted_intent == "weather" or any(kw in lower_q for kw in WEATHER_KEYWORDS):
        target_district = district if district != "Unknown" else None
        if target_district:
            weather_data = await weather_service.get_imd_forecast(target_district)
            extra_context += f"\nIMD Weather for {target_district}: {weather_data}\n"
        else:
            extra_context += "\nIMD Weather Info: I don't know your district. Please tell me your district name for weather updates.\n"

    if not retriever:
        logger.warning("Retriever missing. Falling back to local sample data.")
        import json
        try:
            with open(os.path.join("data", "sample_dataset.json"), "r", encoding="utf-8") as f:
                data = json.load(f)
            context_str = "\n\n".join(d["content"] for d in data) + extra_context
        except Exception:
            context_str = "No database connection and no local data found." + extra_context
            
        rag_chain = (
            {
                "context": lambda _: context_str, 
                "question": RunnablePassthrough(),
                "crop": lambda _: crop,
                "district": lambda _: district,
                "intent": lambda _: predicted_intent
            }
            | prompt
            | llm
            | StrOutputParser()
        )
    else:
        rag_chain = (
            {
                "context": lambda q: format_docs(retriever.invoke(q)) + extra_context, 
                "question": RunnablePassthrough(),
                "crop": lambda _: crop,
                "district": lambda _: district,
                "intent": lambda _: predicted_intent
            }
            | prompt
            | llm
            | StrOutputParser()
        )
    
    try:
        rag_response = await rag_chain.ainvoke(question)
        
        # 5. A/B Evaluation Loop (10% of requests)
        if random.random() < 0.10:
            # Generate LLM response without RAG context
            async def run_ab_eval():
                try:
                    direct_prompt = ChatPromptTemplate.from_template("Answer the farmer's question: {question}")
                    llm_chain = direct_prompt | llm | StrOutputParser()
                    llm_response = await llm_chain.ainvoke({"question": question})
                    
                    # Compute heuristic scores
                    length_diff = abs(len(rag_response) - len(llm_response))
                    
                    rag_words = set(rag_response.lower().split())
                    llm_words = set(llm_response.lower().split())
                    intersection = len(rag_words.intersection(llm_words))
                    union = len(rag_words.union(llm_words))
                    overlap_score = intersection / union if union > 0 else 0.0
                    
                    # Log asynchronously to DB
                    await asyncio.to_thread(log_ab_eval, question, rag_response, llm_response, length_diff, overlap_score)
                except Exception as eval_err:
                    logger.error(f"A/B Eval failed: {eval_err}")
                    
            asyncio.create_task(run_ab_eval())
            
        return rag_response
    except Exception as e:
        logger.error(f"RAG Pipeline failed: {str(e)}", exc_info=True)
        return "માફ કરો, ∘ ∘ ∘ ∘ ∘. / क्षमा करें, मैं अभी इस सवाल का जवाब देने में असमर्थ हूँ।"

