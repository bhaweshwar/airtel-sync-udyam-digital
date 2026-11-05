# Demo script (2:50)

One take, recorded at phone width (390 × 844) on the deployed app, with demo mode on. The narration is in English. The advisor input is spoken in Hindi. Keep the narration to the times below: the video limit is 3:00, and 10 s are spare.

**Before recording**
- Wake the Render service.
- Open the landing page in a fresh browser profile, so no journey is stored.
- Allow the microphone, set the volume, and have the back-office passcode ready.
- Close every other tab.

| Time | Screen | Do (type / click / say) | Narration |
|---|---|---|---|
| **0:00–0:15** | Landing | Show the landing page, then tap **हिंदी** to switch the UI to Hindi. | "Only 7.4% of Accel Business's small-business leads activate, and it takes 17.6 days. Udyam Digital lets an owner go from a question to a live connection on a phone, in their own language." |
| **0:15–0:50** | Advisor | Tap the mic and say: *"मेरा पुणे में डेंटल क्लिनिक है, छह लोग काम करते हैं। अभी घर वाला ब्रॉडबैंड है, मुझे तेज़ इंटरनेट, ईमेल और मरीज़ों का डेटा सुरक्षित रखना है।"* Answer any one follow-up question it asks (for example GSTIN: *"हाँ, GST है"*). | "A dentist in Pune asks in Hindi, by voice. The advisor asks only what is missing. Then it recommends a bundle, with a plain-language reason for each item." |
| **0:50–1:05** | Advisor → Quote | Point at the reasons on two line items, then tap **See quote / कोटेशन देखें**. | "The rules engine picks the products and prices from the catalogue. The LLM only explains, so it can't invent a plan or a price." |
| **1:05–1:25** | Quote | Toggle **Cloud CCTV** on. Show the dependency notice and the monthly total updating with GST. Tap **Confirm order**, enter contact name *Dr. Meera Kulkarni* and a test phone *9800000001*, then submit. | "One monthly price, and add-ons the owner can toggle. CCTV needs a broadband line, and the quote says so. The owner confirms in one tap and gets an order ID and a PIN." |
| **1:25–1:40** | KYC consent | Show the consent screen: purposes, retention, EN/HI. Tick the required purpose only, then tap **Agree**. | "Consent is per purpose and versioned. Photos are read in memory and never stored. Withdrawing consent deletes the KYC data." |
| **1:40–2:00** | KYC: K11 | Tap **Try a sample applicant → K11**. Show the result **Action required**: the address-proof bill is older than 90 days, with a retake hint. | "Smart KYC reads the GST certificate, Udyam certificate, ID and bill, then checks them against the registries. Here the electricity bill is stale, so the owner is asked to retake just that one photo. Nobody has to visit." |
| **2:00–2:15** | KYC: K03 | Tap **Try a sample applicant → K03**. Show **Verified**, with every check passing and identifiers masked. | "With valid documents, verification takes seconds. Every identifier is masked on screen and in the logs." |
| **2:15–2:35** | Tracker | Open the tracker. Book the first available install slot. Tap **Advance (demo)** until the status reaches **Live**. | "Instead of calling support three times, the owner books an install slot and watches each step, with a date for each item, until the service is live." |
| **2:35–2:50** | Back office | Open `/backoffice` and enter the passcode. Show the ranked leads, each with a score, HOT/WARM/COLD band, top two factors and suggested channel (FIELD / PARTNER / SELF_SERVE_LINK). | "Leads the advisor can't close land here, ranked by a propensity score. Multi-site and manufacturers go to the field force, micro and tier-2 leads go to partners, and leads we can't reach get a self-serve link. Udyam Digital adds to the field force instead of competing with it." |

**Fallbacks while recording**
- **Voice:** if speech recognition fails, type the same Hindi sentence into the advisor box. Do not re-record.
- **LLM status:** if the LLM status badge shows **rules** mode, keep going. The flow is the same, and it shows the fallback working.
- **K11:** if K11 gives a different verdict, say "the owner is told exactly which document to fix" and move on to K03.

**Cut list** (if the take runs long, drop these first)
1. The second line-item reason at 0:50.
2. The slot-booking close-up at 2:15.
