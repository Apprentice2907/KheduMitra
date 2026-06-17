def test_twilio_incoming_call(client):
    response = client.post("/api/v1/twilio/voice/incoming")
    assert response.status_code == 200
    assert "<Gather action=\"/twilio/voice/menu\"" in response.text
    assert "<Record action=\"/twilio/voice/recording?lang=hi\"" in response.text

def test_twilio_menu_hindi(client):
    response = client.post("/api/v1/twilio/voice/menu", data={"Digits": "1"})
    assert response.status_code == 200
    assert "language=\"hi-IN\"" in response.text

def test_whatsapp_webhook_verification(client):
    response = client.get(
        "/api/v1/whatsapp/webhook", 
        params={
            "hub.mode": "subscribe",
            "hub.challenge": "12345",
            "hub.verify_token": "khedumitra_secret"
        }
    )
    assert response.status_code == 200
    assert response.text == "12345"
