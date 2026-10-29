from contextlib import asynccontextmanager
from typing import AsyncGenerator, List, Optional
from fastapi import FastAPI, HTTPException, Depends, status
from sqlmodel import Field, SQLModel, select
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

# --- DATABASE SETUP ---
DATABASE_URL = "sqlite+aiosqlite:///./attendance.db"
engine = create_async_engine(DATABASE_URL, echo=True)
async_session_pool = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    yield

app = FastAPI(title="Contact Form API", lifespan=lifespan)

# --- DEPENDENCY INJECTION ---
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_pool() as session:
        yield session

# --- DATA MODEL ---
class ContactForm(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    email: str
    message: str

# --- CRUD ENDPOINTS ---

# 1. CREATE SUBMISSION (Submit Contact Form)
@app.post("/contact", response_model=ContactForm, status_code=status.HTTP_201_CREATED)
async def create_contact_submission(form_in: ContactForm, db: AsyncSession = Depends(get_session)):
    db.add(form_in)
    await db.commit()
    await db.refresh(form_in)
    return form_in

# 2. READ ALL SUBMISSIONS
@app.get("/contact", response_model=List[ContactForm])
async def read_all_submissions(db: AsyncSession = Depends(get_session)):
    statement = select(ContactForm)
    results = await db.execute(statement)
    return results.scalars().all()

# 3. READ ONE SUBMISSION BY ID
@app.get("/contact/{form_id}", response_model=ContactForm)
async def read_submission(form_id: int, db: AsyncSession = Depends(get_session)):
    db_form = await db.get(ContactForm, form_id)
    if not db_form:
        raise HTTPException(status_code=404, detail="Submission not found")
    return db_form
