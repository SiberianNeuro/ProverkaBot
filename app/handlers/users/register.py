from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from sqlalchemy import select, and_, func, not_
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker

from app.keyboards.register_kb import RegCallback, get_confirm, get_clusters_keyboard
from app.models.kazarma import KazarmaUser, KazarmaRole
from app.models.user import User
from app.utils.states import Register

router = Router()
router.message.filter(F.chat.type == 'private')
router.callback_query.filter(F.message.chat.type == 'private')


@router.callback_query(RegCallback.filter(F.param == 'register'))
async def get_fullname(call: types.CallbackQuery, state: FSMContext):
    await call.message.answer('Напиши свое ФИО.\n\n<i>Например, Иванов Иван Иванович</i>')
    await state.set_state(Register.fullname)


@router.message(Register.fullname)
async def get_info(msg: types.Message, db_session: sessionmaker, state: FSMContext):
    stmt = select(
        [
            func.CONCAT_WS(' ', KazarmaUser.lastname, KazarmaUser.firstname, KazarmaUser.middlename).label('fullname'),
            KazarmaUser.id,
            KazarmaUser.role_id,
            KazarmaRole.name
        ]
    ).join(KazarmaRole).filter(
        and_(
            func.CONCAT_WS(' ', KazarmaUser.lastname, KazarmaUser.firstname, KazarmaUser.middlename)
            .ilike(msg.text.title().strip()),
            KazarmaUser.active == 1,
            not_(KazarmaUser.email.contains('@mobile.test'))
        )
    )
    async with db_session.begin() as session:
        temp_user = await session.execute(stmt)
        temp_users = temp_user.mappings().all()
        await session.commit()
        for user in temp_users:
            user = {key: value for key, value in user.items()}
            # user = {column.key: getattr(user, attr) for attr, column in user.__mapper__.c.items()}
    if not temp_users:
        await msg.answer('Я не нашел такого пользователя в "Инфоклинике".'
                         ' Пожалуйста, проверь, правильно ли ты заполнил имя.')
    else:
        if len(temp_users) > 1:
            await state.update_data(temp_users=temp_users)
            text = 'Я нашел в "Инфоклинике" следующие аккаунты:\n\n'
            for num, user in enumerate(temp_users, 1):
                text += f'<b>{num}. {user.fullname}</b>\nДолжность: {user.name}'
            text += '\n\nПожалуйста, выбери, какой из них верный'
            await msg.answer(text=text, reply_markup=await get_confirm(temp_users))
        else:
            await state.update_data(temp_users=temp_users[0])
            text = f'Нашел в "Инфоклинике" аккаунт:\n\n' \
                   f'<b>{temp_users[0].fullname}</b>' \
                   f'\nДолжность: {temp_users[0].name}' \
                   f'\nЕсли я прав, пожалуйста, нажми кнопку подтверждения.'
            await msg.answer(text=text, reply_markup=await get_confirm(temp_users[0]))
        await state.set_state(Register.confirm)


@router.callback_query(RegCallback.filter(F.param == 'confirm'), Register.confirm)
async def get_cluster(call: types.CallbackQuery, state: FSMContext, db_session: sessionmaker,
                      callback_data: RegCallback):
    if callback_data.value == 0:
        await call.message.answer('Тогда прошу тебя проверить ФИО и попробовать еще раз.')
        await state.set_state(Register.fullname)
    else:
        user_data = await state.get_data()
        user_data = user_data['temp_users']
        if isinstance(user_data, list):
            for data in user_data:
                if data.id == callback_data.value:
                    user_data = data
                    break
            await state.update_data(temp_users=user_data)
        if user_data.role_id in (5, 17, 29, 30):
            async with db_session.begin() as session:
                session.add(
                    User(
                        id=call.from_user.id,
                        fullname=user_data.fullname,
                        kazarma_id=user_data.id,
                        role_id=user_data.role_id,
                        role_name=user_data.name,
                        cluster_id=18,
                        is_checking=False,
                        is_admin=True,
                        clients_count=0
                    )
                )
                await session.commit()
            await call.message.answer('Вы определены как администратор. Добро пожаловать! Что я умею:\n\n')
        else:
            await call.message.answer('Осталось узнать, к какой команде ты принадлежишь. Выбирай:',
                                      reply_markup=await get_clusters_keyboard(db_session))
