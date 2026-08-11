import asyncio
from app.core.database import AsyncSessionLocal
from app.models.user import User
from app.core.security import hash_password

async def create_admin():
    # Open an async session
    async with AsyncSessionLocal() as db:
        admin_user = User(
            email='admin01@example.com', 
            password_hash=hash_password('admin'), 
            role='admin', 
            is_active=True
        )
        db.add(admin_user)
        await db.commit()
        print("✅ Admin user created successfully!")
        print("Email: admin@example.com")
        print("Password: admin")

if __name__ == "__main__":
    asyncio.run(create_admin())