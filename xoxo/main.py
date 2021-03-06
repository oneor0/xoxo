import uuid
from datetime import timedelta

from fastapi import Depends, FastAPI, Form, HTTPException
from fastapi import status as http_status
from fastapi.security import OAuth2PasswordRequestForm

from xoxo.auth import authenticate_user, create_access_token, get_current_user
from xoxo.db import (
    create_move,
    create_user,
    database,
    get_last_move,
    get_user,
    get_session_moves,
    get_session_time,
)
from xoxo.game import (
    Status,
    check_board_status,
    create_board,
    find_best_move,
    make_move,
    print_board,
)
from xoxo.schemas import Move, User

ACCESS_TOKEN_EXPIRE_MINUTES = 60


app = FastAPI(
    title="Tic Tac Toe",
    description=(
        "This service provides an API to play "
        "tic tac toe game against computer opponent."
    ),
)


@app.on_event("startup")
async def startup():
    await database.connect()


@app.on_event("shutdown")
async def shutdown():
    await database.disconnect()


@app.post("/play/")
async def play(move: Move, current_user: User = Depends(get_current_user)):
    last_move = await get_last_move(current_user.id)
    session = uuid.uuid4()
    if last_move and last_move["status"] == Status.ACTIVE:
        board = last_move["board"]
        session = last_move["session"]
    else:
        board = create_board(move.size)

    make_move(board, (move.row, move.col), True)
    status = check_board_status(board)

    await create_move(
        row=move.row,
        col=move.col,
        is_ai=False,
        status=status,
        board=board,
        session=session,
        user_id=current_user.id,
    )

    ai_move = None
    if status not in (Status.TIE, Status.WON):
        ai_move = find_best_move(board)
        make_move(board, ai_move, False)
        status = check_board_status(board)

        await create_move(
            row=ai_move[0],
            col=ai_move[1],
            is_ai=True,
            status=status,
            board=board,
            session=session,
            user_id=current_user.id,
        )

    print_board(board)

    if status != Status.ACTIVE:
        moves = await get_session_moves(session)
        session_time = await get_session_time(session)
        return {"status": status, "session_time": session_time, "moves": moves}

    return {"status": status, "move": ai_move, "board": board}


@app.post("/login/")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = await authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=http_status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )

    return {"access_token": access_token, "token_type": "bearer"}


@app.post("/register/", status_code=http_status.HTTP_201_CREATED)
async def register(
    username: str = Form(..., min_length=3, max_length=50),
    password: str = Form(..., min_length=3, max_length=50, regex=r"^\w+$"),
):
    if await get_user(username):
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="User with this username already exists.",
        )

    await create_user(username, password)
