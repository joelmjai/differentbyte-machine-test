from contextlib import asynccontextmanager
from typing import AsyncGenerator, List, Optional
from fastapi import FastAPI, HTTPException, Depends, status
from sqlmodel import Field, SQLModel, select
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

# 1. Database File Configuration
DATABASE_URL = "sqlite+aiosqlite:///./students.db"
engine = create_async_engine(DATABASE_URL, echo=True)
async_session_pool = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# 2. Automatically create database tables when the app starts
@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    yield

app = FastAPI(title="Student Management API", lifespan=lifespan)

# 3. Database Session Dependency
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_pool() as session:
        yield session

# 4. Student Table Blueprint
class StudentBase(SQLModel):
    name: str = Field(index=True)
    age: int = Field(gt=0)
    grade: str

class Student(StudentBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)

class StudentCreate(StudentBase):
    pass

class StudentUpdate(SQLModel):
    name: Optional[str] = None
    age: Optional[int] = Field(None, gt=0)
    grade: Optional[str] = None


# 5. CRUD Endpoints

# CREATE - Add a student
@app.post("/students", response_model=Student, status_code=status.HTTP_201_CREATED)
async def create_student(student_in: StudentCreate, db: AsyncSession = Depends(get_session)):
    db_student = Student.model_validate(student_in)
    db.add(db_student)
    await db.commit()
    await db.refresh(db_student)
    return db_student

# READ ALL - View all students
@app.get("/students", response_model=List[Student])
async def read_students(offset: int = 0, limit: int = 100, db: AsyncSession = Depends(get_session)):
    statement = select(Student).offset(offset).limit(limit)
    results = await db.execute(statement)
    return results.scalars().all()

# READ ONE - View single student by ID
@app.get("/students/{student_id}", response_model=Student)
async def read_student(student_id: int, db: AsyncSession = Depends(get_session)):
    db_student = await db.get(Student, student_id)
    if not db_student:
        raise HTTPException(status_code=404, detail="Student not found")
    return db_student

# UPDATE - Edit a student's info
@app.patch("/students/{student_id}", response_model=Student)
async def update_student(student_id: int, student_in: StudentUpdate, db: AsyncSession = Depends(get_session)):
    db_student = await db.get(Student, student_id)
    if not db_student:
        raise HTTPException(status_code=404, detail="Student not found")
    
    update_data = student_in.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_student, key, value)
        
    db.add(db_student)
    await db.commit()
    await db.refresh(db_student)
    return db_student

# DELETE - Remove a student
@app.delete("/students/{student_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_student(student_id: int, db: AsyncSession = Depends(get_session)):
    db_student = await db.get(Student, student_id)
    if not db_student:
        raise HTTPException(status_code=404, detail="Student not found")
    
    await db.delete(db_student)
    await db.commit()
    return
