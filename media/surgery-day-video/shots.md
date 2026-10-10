# Realistic footage shot list

Generate each shot as a **16:9, 1080p, 8-second clip with no audio and no on-screen text**, using a
realistic text-to-video tool such as Gemini/Veo, Sora, Runway or Kling. Save each clip as
`clips/<file name>.mp4`, then run `python3 assemble.py vo/ clips/ out/`. The voiceover, subtitles,
step cards and music are added automatically, and each clip is fitted to the length of its scene.
Any shot you leave out falls back to the illustrated version of that scene, so you can build the
video a few clips at a time.

Add this **style line to every prompt** so the shots look consistent:

> Photorealistic documentary-style hospital footage, bright soft natural lighting, clean modern
> Sri Lankan hospital orthopaedic ward, calm reassuring mood, shallow depth of field, slow smooth
> camera movement, 35mm film look, no text, no logos, no gore, no needles shown piercing skin.

Keep the same patient throughout: *a Sri Lankan woman in her 50s, shoulder-length black hair tied
back, wearing a light-blue patterned hospital gown*. If your tool supports a reference image, reuse
the first good frame of her to keep her face consistent.

| File | Scene | Prompt |
|---|---|---|
| `welcome_1` | Welcome | Slow dolly-in along a bright, tidy hospital ward with white beds, sunlight through large windows, a nurse in teal scrubs walking calmly in the background. |
| `welcome_2` | Welcome | A smiling South Asian female nurse in teal scrubs with a stethoscope greets the patient, who is sitting up in her hospital bed. The nurse gently touches the patient's shoulder and the patient smiles back, relaxed. |
| `prep_1` | Step 1 | Close-up of a nurse's gloved hands holding the patient's wrist and reading the white patient identification wristband, then scanning it with a small handheld barcode scanner. |
| `prep_2` | Step 1 | The patient, now in a light-blue hospital gown, sits on the edge of her bed behind a privacy curtain and folds her clothes neatly. |
| `prep_3` | Step 1 | Close-up of the patient placing her glasses, a wristwatch, a ring and a small denture cup into a labelled clear plastic property bag on a bedside table. A nurse nods reassuringly. |
| `transfer_1` | Step 2 | Two porters in scrubs gently wheel the patient, lying on a hospital trolley under a white blanket, out of the ward. Tracking shot from beside the trolley; the patient looks calm. |
| `transfer_2` | Step 2 | Point-of-view shot from the trolley moving slowly down a clean, bright hospital corridor, ceiling lights passing overhead, towards double doors marked "Theatres". |
| `transfer_3` | Step 2 | A theatre nurse in a blue scrub cap and the anaesthetist meet the trolley at the theatre doors. They smile, and the nurse checks the patient's wristband against a clipboard. |
| `anaesthesia_1` | Step 3 | Close-up: a pulse oximeter clip is placed on the patient's finger and a red light glows softly; a blood pressure cuff on her upper arm gently inflates. |
| `anaesthesia_2` | Step 3 | A patient monitor beside the bed shows a steady green ECG trace, heart rate 72 and SpO2 98%. Shallow focus, with the anaesthetist blurred in the background. |
| `anaesthesia_3` | Step 3 | A friendly male anaesthetist in a blue scrub cap, with his mask lowered, leans over and talks reassuringly to the patient lying on the trolley. She nods and slowly closes her eyes, peaceful. The lights soften. |
| `recovery_1` | Step 4 | In a quiet recovery room with soft warm lighting, the patient lies in bed under a blanket and slowly opens her eyes, looking sleepy but comfortable. |
| `recovery_2` | Step 4 | A recovery nurse in teal scrubs smiles and tucks a warm blanket around the patient, then checks the vital-signs monitor on the wall. |
| `recovery_3` | Step 4 | Close-up of the nurse gently asking the patient a question, and the patient giving a small thumbs-up. |
| `ward_1` | Step 5 | The patient is wheeled back into the bright orthopaedic ward on her bed by two staff members and parked beside a sunny window. |
| `ward_2` | Step 5 | The patient, sitting up in bed, sips water from a cup through a straw. A family member sitting beside the bed smiles and holds her hand. |
| `ward_3` | Step 5 | Close-up of the patient's hand resting near a nurse call-bell handset clipped to the bed rail; her thumb rests on the red button. |
| `outro_1` | Outro | A group of four smiling orthopaedic ward staff (nurses and a doctor in a white coat) stand together at the nurses' station and wave warmly at the camera. |
| `outro_2` | Outro | Slow pull-back from the patient resting comfortably in bed and smiling, with sunlight through the window. |

Tips:
- If a tool adds text or garbled signage, regenerate or crop it out. On-screen text is added in post.
- Avoid prompts showing incisions, needles going in or surgery itself. Patients find those distressing.
- Check every clip for clinical accuracy (gloves, wristbands, monitor placement) before using it.
