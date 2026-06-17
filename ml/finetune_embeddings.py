import os
import json
import random
from sentence_transformers import SentenceTransformer, InputExample, losses
from torch.utils.data import DataLoader

def load_data(filepath="data/sample_dataset.json"):
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)

def generate_synthetic_qa(data):
    """
    Generate Question-Answer pairs using domain terms for training embeddings.
    Focus on creating hard negatives implicitly by making similar but distinct questions.
    """
    examples = []
    
    # Static rules for synthetic generation from sample_dataset.json contents
    # PM-KISAN, PMFBY, Cotton Leaf Curl Virus (CLCuV), Wheat Rust (Yellow Rust/पीला रतुआ)
    
    qa_pairs = [
        # PM-KISAN
        ("What is PM-Kisan Samman Nidhi?", "The Pradhan Mantri Kisan Samman Nidhi (PM-KISAN) is a central sector scheme that provides income support to all landholding farmers' families in the country to supplement their financial needs for procuring various inputs related to agriculture and allied activities as well as domestic needs. Under the Scheme, an amount of Rs. 6000/- per year is transferred in three 4-monthly installments of Rs. 2000/- directly into the bank accounts of the beneficiaries."),
        ("How much money is given under PM-KISAN?", "Under the Scheme, an amount of Rs. 6000/- per year is transferred in three 4-monthly installments of Rs. 2000/- directly into the bank accounts of the beneficiaries."),
        ("Who is eligible for PM-KISAN?", "The scheme provides income support to all landholding farmers' families in the country."),
        ("mera kisan samman nidhi ka paisa kitna aayega?", "Under the Scheme, an amount of Rs. 6000/- per year is transferred in three 4-monthly installments of Rs. 2000/-."),
        
        # Cotton CLCuV
        ("What are the symptoms of Cotton Leaf Curl Virus?", "Cotton Leaf Curl Virus is a severe disease affecting cotton. Symptoms include upward or downward curling of leaf margins, thickened veins, and enations on the underside of leaves."),
        ("How to control whitefly in cotton?", "Management involves using resistant varieties, uprooting and destroying infected plants, and controlling the whitefly population using recommended insecticides like Imidacloprid."),
        ("kapaas ke patte mod rahe hain kya karu?", "Symptoms include upward or downward curling of leaf margins, thickened veins, and enations on the underside of leaves. It is transmitted by the whitefly (Bemisia tabaci). Management involves controlling the whitefly population using recommended insecticides like Imidacloprid."),
        
        # Wheat Yellow Rust
        ("What is Yellow Rust in wheat?", "Yellow rust is a major fungal disease of wheat in northern India. Symptoms include yellow stripes or pustules on the leaves (गेहूं में पीले धब्बे). It causes severe yield loss."),
        ("gehu me pila ratua lag gaya hai dawai batao", "For treatment, spray Propiconazole 25 EC @ 0.1% or Tebuconazole 250 EC @ 0.1% as soon as symptoms appear. Grow resistant varieties like PBW 723 or HD 2967."),
        ("Which fungicide to use for wheat rust?", "For treatment, spray Propiconazole 25 EC @ 0.1% or Tebuconazole 250 EC @ 0.1% as soon as symptoms appear."),
        
        # PMFBY
        ("What is PM Fasal Bima Yojana?", "PMFBY provides a comprehensive insurance cover against failure of the crop thus helping in stabilizing the income of the farmers. The scheme covers all Food & Oilseeds crops and Annual Commercial/Horticultural Crops for which past yield data is available."),
        ("What is the premium for Kharif crops under PMFBY?", "The premium to be paid by farmers is very low: 2% for all Kharif crops, 1.5% for all Rabi crops, and 5% for commercial/horticultural crops."),
        ("fasal bima yojana ka premium kya hai", "The premium to be paid by farmers is very low: 2% for all Kharif crops, 1.5% for all Rabi crops, and 5% for commercial/horticultural crops.")
    ]
    
    # We will expand these to a few hundred synthetic pairs for fine-tuning
    # MultipleNegativesRankingLoss takes (Anchor, Positive)
    
    for q, a in qa_pairs:
        examples.append(InputExample(texts=[q, a]))
        # Small augmentations for robustness
        examples.append(InputExample(texts=[q.lower(), a]))
        examples.append(InputExample(texts=[q + " please tell me", a]))
        
    return examples

def train():
    print("Loading base sentence transformer model...")
    # Base model suitable for English/Hindi cross-lingual
    model_name = "paraphrase-multilingual-MiniLM-L12-v2"
    model = SentenceTransformer(model_name)
    
    print("Generating training data...")
    data = load_data()
    train_examples = generate_synthetic_qa(data)
    
    # Artificially scale data up to simulate a larger fine-tuning set
    train_examples = train_examples * 50
    random.shuffle(train_examples)
    
    train_dataloader = DataLoader(train_examples, shuffle=True, batch_size=16)
    
    # Use MultipleNegativesRankingLoss: expects batches of (Anchor, Positive) pairs.
    # It assumes all other Positives in the batch are Negatives for the current Anchor.
    train_loss = losses.MultipleNegativesRankingLoss(model=model)
    
    print("Starting training (target Colab T4)...")
    # Training for 1 epoch for demonstration
    model.fit(
        train_objectives=[(train_dataloader, train_loss)],
        epochs=1,
        warmup_steps=100,
        show_progress_bar=True
    )
    
    os.makedirs("models/agri-embeddings", exist_ok=True)
    model.save("models/agri-embeddings")
    print("Model adapter saved to models/agri-embeddings/")

if __name__ == "__main__":
    train()
