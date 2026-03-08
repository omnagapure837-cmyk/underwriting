from web_app import build_documents_from_form


def test_build_documents_from_form():
    proposal, medical = build_documents_from_form(
        {
            "identity": "Jane Doe",
            "age": "44",
            "gender": "Female",
            "occupation": "teacher",
            "income": "70000",
            "smoking": "No",
            "alcohol": "social",
            "riders": "Accident",
            "medical_conditions": "Asthma(Mild)",
        }
    )

    assert "Identity: Jane Doe" in proposal
    assert "Age: 44" in proposal
    assert "Riders: Accident" in proposal
    assert medical == "Medical Conditions: Asthma(Mild)"
