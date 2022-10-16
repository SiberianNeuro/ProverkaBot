from aiogram.fsm.state import StatesGroup, State


class Register(StatesGroup):

    fullname = State()
    cluster = State()
    confirm = State()


class FSMTicket(StatesGroup):

    id = State()
    confirm = State()


class Checking(StatesGroup):

    choice = State()
    comment = State()
