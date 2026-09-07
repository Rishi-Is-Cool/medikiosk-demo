import os
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont


def create_sample_documents(output_dir: Path):
    output_dir.mkdir(parents=True, exist_ok=True)

    # 1. Prescription (DOC_001)
    img_rx = Image.new("RGB", (800, 1000), color=(255, 255, 255))
    draw_rx = ImageDraw.Draw(img_rx)
    
    draw_rx.rectangle([(20, 20), (780, 980)], outline=(40, 60, 120), width=3)
    draw_rx.rectangle([(25, 25), (775, 120)], fill=(240, 245, 255))
    draw_rx.text((40, 35), "CITY CLINIC & MEDICAL CENTRE", fill=(20, 40, 100))
    draw_rx.text((40, 60), "Dr. R. Sharma, MD (Medicine) | Reg No: DMC-48291", fill=(60, 60, 60))
    draw_rx.text((40, 85), "12 Hospital Road, New Delhi | Ph: 011-23456789", fill=(100, 100, 100))
    
    draw_rx.line([(25, 120), (775, 120)], fill=(40, 60, 120), width=2)
    draw_rx.text((40, 140), "Date: 2019-05-10          Patient Name: Rajesh Kumar (Age: 48 / M)", fill=(0, 0, 0))
    draw_rx.line([(25, 170), (775, 170)], fill=(200, 200, 200), width=1)

    draw_rx.text((40, 190), "DIAGNOSIS (Dx):", fill=(20, 40, 100))
    draw_rx.text((60, 215), "1. DM (Type 2 Diabetes Mellitus)", fill=(0, 0, 0))
    draw_rx.text((60, 240), "2. HTN (Essential Hypertension)", fill=(0, 0, 0))

    draw_rx.text((40, 280), "KNOWN ALLERGIES:", fill=(180, 30, 30))
    draw_rx.text((60, 305), "• Penicillin (Causes skin rash / urticaria)", fill=(180, 30, 30))

    draw_rx.text((40, 350), "Rx (MEDICATIONS):", fill=(20, 40, 100))
    draw_rx.text((60, 380), "1. Tab. Metformin 500 mg — 1 Tab BD (Twice Daily) after meals x 1 Month", fill=(0, 0, 0))
    draw_rx.text((60, 420), "2. Tab. Telmisartan 40 mg — 1 Tab OD (Once Daily) morning x 1 Month", fill=(0, 0, 0))

    draw_rx.text((40, 500), "CLINICAL ADVICE & FOLLOW-UP:", fill=(20, 40, 100))
    draw_rx.text((60, 530), "• Diabetic diet, regular 30 mins brisk walking.", fill=(0, 0, 0))
    draw_rx.text((60, 560), "• Monitor BP and blood sugar weekly.", fill=(0, 0, 0))
    draw_rx.text((60, 590), "• Review in OPD after 1 month with Fasting Blood Sugar.", fill=(0, 0, 0))

    draw_rx.text((550, 900), "Dr. R. Sharma", fill=(20, 40, 100))
    draw_rx.text((530, 925), "[Signature & Stamp]", fill=(120, 120, 120))

    img_rx.save(output_dir / "prescription_01.jpg", quality=95)

    # 2. Lab Report (DOC_002)
    img_lab = Image.new("RGB", (800, 1000), color=(255, 255, 255))
    draw_lab = ImageDraw.Draw(img_lab)

    draw_lab.rectangle([(20, 20), (780, 980)], outline=(0, 100, 80), width=3)
    draw_lab.rectangle([(25, 25), (775, 120)], fill=(235, 250, 245))
    draw_lab.text((40, 35), "APEX DIAGNOSTIC CENTRE & PATHOLOGY LAB", fill=(0, 80, 60))
    draw_lab.text((40, 60), "Accredited NABL Lab | ISO 15189 Certified", fill=(60, 60, 60))
    draw_lab.text((40, 85), "Report Date: 2026-08-15 | Patient: Rajesh Kumar (Age: 55 / M)", fill=(100, 100, 100))

    draw_lab.line([(25, 130), (775, 130)], fill=(0, 100, 80), width=2)
    draw_lab.text((40, 150), "TEST NAME                     RESULT       UNIT        REFERENCE INTERVAL", fill=(0, 60, 50))
    draw_lab.line([(25, 175), (775, 175)], fill=(0, 100, 80), width=1)

    draw_lab.text((40, 200), "HbA1c (Glycated Hb)          8.2          %           < 5.7 %  [HIGH / ABNORMAL]", fill=(180, 20, 20))
    draw_lab.text((40, 240), "Fasting Blood Glucose        164          mg/dL       70 - 99 mg/dL  [HIGH]", fill=(180, 20, 20))
    draw_lab.text((40, 280), "Serum Creatinine             0.9          mg/dL       0.6 - 1.2 mg/dL", fill=(0, 0, 0))
    draw_lab.text((40, 320), "Total Cholesterol            190          mg/dL       < 200 mg/dL", fill=(0, 0, 0))
    draw_lab.text((40, 360), "Serum Sodium (Na+)           138          mEq/L       135 - 145 mEq/L", fill=(0, 0, 0))

    draw_lab.rectangle([(40, 450), (760, 600)], outline=(180, 180, 180), fill=(250, 250, 250))
    draw_lab.text((50, 465), "INTERPRETATION & PATHOLOGIST REMARKS:", fill=(0, 60, 50))
    draw_lab.text((50, 495), "• HbA1c >= 6.5% is diagnostic of Diabetes Mellitus. Patient's value of 8.2%", fill=(0, 0, 0))
    draw_lab.text((50, 520), "  indicates suboptimal glycemic control over the past 3 months.", fill=(0, 0, 0))
    draw_lab.text((50, 545), "• Fasting blood glucose is significantly elevated.", fill=(0, 0, 0))

    draw_lab.text((500, 900), "Dr. A. K. Verma, MD (Path)", fill=(0, 60, 50))
    draw_lab.text((500, 925), "Consultant Pathologist", fill=(100, 100, 100))

    img_lab.save(output_dir / "lab_report_01.jpg", quality=95)

    # 3. Discharge Summary (DOC_003)
    img_ds = Image.new("RGB", (800, 1000), color=(255, 255, 255))
    draw_ds = ImageDraw.Draw(img_ds)

    draw_ds.rectangle([(20, 20), (780, 980)], outline=(120, 40, 40), width=3)
    draw_ds.rectangle([(25, 25), (775, 120)], fill=(255, 245, 245))
    draw_ds.text((40, 35), "METRO SUPERSPECIALITY HOSPITAL", fill=(100, 20, 20))
    draw_ds.text((40, 60), "DEPARTMENT OF GENERAL MEDICINE & GASTROENTEROLOGY", fill=(60, 60, 60))
    draw_ds.text((40, 85), "DISCHARGE SUMMARY | IPD No: IP-94021", fill=(100, 100, 100))

    draw_ds.line([(25, 130), (775, 130)], fill=(120, 40, 40), width=2)
    draw_ds.text((40, 145), "Patient: Rajesh Kumar | Age: 53 / M | Adm: 2024-11-18 | Disch: 2024-11-20", fill=(0, 0, 0))
    draw_ds.line([(25, 175), (775, 175)], fill=(200, 200, 200), width=1)

    draw_ds.text((40, 195), "FINAL DIAGNOSIS:", fill=(100, 20, 20))
    draw_ds.text((60, 220), "• Acute Gastroenteritis with Moderate Dehydration (Resolved)", fill=(0, 0, 0))
    draw_ds.text((60, 245), "• Type 2 Diabetes Mellitus (Underlying Chronic)", fill=(0, 0, 0))

    draw_ds.text((40, 285), "ALLERGIES RECORDED:", fill=(180, 20, 20))
    draw_ds.text((60, 310), "• Penicillin (Reported severe urticaria on previous exposure)", fill=(180, 20, 20))

    draw_ds.text((40, 350), "HOSPITAL COURSE & PROCEDURES:", fill=(100, 20, 20))
    draw_ds.text((60, 375), "• IV Fluid resuscitation (RL + DNS) administered.", fill=(0, 0, 0))
    draw_ds.text((60, 400), "• Inj. Ceftriaxone 1g IV BD administered for 3 days.", fill=(0, 0, 0))
    draw_ds.text((60, 425), "• Patient stabilized and discharged in afebrile, healthy condition.", fill=(0, 0, 0))

    draw_ds.text((40, 470), "DISCHARGE MEDICATIONS:", fill=(100, 20, 20))
    draw_ds.text((60, 495), "1. Tab Pantoprazole 40 mg OD before breakfast x 5 days", fill=(0, 0, 0))
    draw_ds.text((60, 520), "2. Resume home medications (Metformin, Telmisartan)", fill=(0, 0, 0))

    draw_ds.text((500, 900), "Dr. Sunita Rao, MS", fill=(100, 20, 20))
    draw_ds.text((500, 925), "Attending Physician", fill=(100, 100, 100))

    img_ds.save(output_dir / "discharge_summary_01.jpg", quality=95)
    print(f"Generated 3 sample documents in {output_dir}")


if __name__ == "__main__":
    docs_path = Path(__file__).resolve().parent
    create_sample_documents(docs_path)
