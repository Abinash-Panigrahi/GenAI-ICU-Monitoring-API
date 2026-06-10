from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import AsyncSessionLocal
from app.services.report_generator import process_patient
from app.models.patient import Patient
from sqlalchemy import select

scheduler = AsyncIOScheduler()

async def run_monitoring_cycle():
    print("⏰ Scheduler triggered — starting monitoring cycle...")
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Patient).where(Patient.is_active == True)
        )
        patients = result.scalars().all()

        if not patients:
            print("⚠️ No active patients found")
            return

        for patient in patients:
            try:
                print(f"🔄 Processing patient {patient.patient_mrn}...")
                await process_patient(patient.patient_mrn, db)
                print(f"✅ Report generated for {patient.patient_mrn}")
            except Exception as e:
                print(f"❌ Failed for {patient.patient_mrn}: {str(e)}")

def start_scheduler():
    scheduler.add_job(
        run_monitoring_cycle,
        trigger=IntervalTrigger(minutes=1),
        id="monitoring_cycle",
        replace_existing=True
    )
    scheduler.start()
    print("✅ Scheduler started — running every 15 minutes")

def stop_scheduler():
    scheduler.shutdown()
    print("Scheduler stopped")