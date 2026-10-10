"""Scenes, narration and on-screen text for the "What to Expect on Surgery Day" patient video."""

TITLE = "Your Surgery Day"
SUBTITLE = "Step-by-Step"
WARD = "Orthopaedic Ward"

# Each narration entry is one TTS sentence; subtitles are split further for readability.
SCENES = [
    {
        "id": "welcome",
        "badge": "WELCOME",
        "heading": "Welcome to your surgery day!",
        "bullets": ["We are here to guide you every step of the way."],
        "narration": [
            "Welcome to the ward.",
            "Feeling a bit nervous before surgery is completely normal.",
            "To help you feel prepared and relaxed, let's walk through what your day will look like, from start to finish.",
        ],
    },
    {
        "id": "prep",
        "badge": "STEP 1",
        "heading": "Morning Prep",
        "bullets": ["Wear your theatre gown", "Remove jewellery, watches and dentures"],
        "narration": [
            "Your day begins right here in the ward.",
            "Our nursing team will help you get ready.",
            "You will change into a clean hospital gown.",
            "We will ask you to remove any jewellery, hairpins, dentures, or glasses for your safety, and check your identification band.",
        ],
    },
    {
        "id": "transfer",
        "badge": "STEP 2",
        "heading": "Heading to Theatre",
        "bullets": ["Our team transports you safely", "Anaesthetist and theatre staff welcome you"],
        "narration": [
            "When it is time, you will be comfortably wheeled down to the operating theatre suite by our staff.",
            "Don't worry, you won't be alone.",
            "Our theatre nurses and your anaesthetist will greet you as soon as you arrive, double-checking your details to ensure everything is correct.",
        ],
    },
    {
        "id": "anaesthesia",
        "badge": "STEP 3",
        "heading": "Meeting Your Anaesthetist",
        "bullets": ["Gentle monitoring equipment attached", "Drifting off to sleep peacefully"],
        "narration": [
            "Next, you will enter the anaesthesia area.",
            "We will attach gentle monitoring stickers to your chest, a blood pressure cuff on your arm, and a small clip on your finger to monitor your breathing and heart rate.",
            "Your anaesthetist will talk to you, place a small IV line in your hand or arm, and before you know it, you will drift off into a safe, deep sleep.",
        ],
    },
    {
        "id": "recovery",
        "badge": "STEP 4",
        "heading": "Recovery Room",
        "bullets": ["Waking up safely", "Nurses monitoring your comfort and pain levels"],
        "narration": [
            "When your surgery is finished, you will wake up in the Post-Anaesthesia Care Unit, often called the recovery room.",
            "You might feel a little sleepy or groggy.",
            "Our dedicated recovery nurses will be right by your side, monitoring your vital signs, keeping you warm, and making sure your pain is well-managed.",
        ],
    },
    {
        "id": "ward",
        "badge": "STEP 5",
        "heading": "Back to the Ward",
        "bullets": ["Rest, hydrate, and start healing", "We are always just a call bell away"],
        "narration": [
            "Once you are fully awake and stable, you will be transferred back to your bed in the orthopaedic ward.",
            "Here, you can rest, sip some water when permitted, and begin your recovery journey with our team supporting you.",
            "Remember, we are always just a call bell away.",
        ],
    },
    {
        "id": "outro",
        "badge": "QUESTIONS?",
        "heading": "Ask your doctor or nurse!",
        "bullets": ["Wishing you a smooth recovery."],
        "narration": [
            "If you have any questions at all about your procedure today, please don't hesitate to ask your doctor or nurse.",
            "We are here for you.",
            "Wishing you a very smooth recovery.",
        ],
    },
]
