from contextlib import suppress
from typing import Union

from aiogram import Router, F, types, Bot
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import ForceReply
from loguru import logger
from sqlalchemy import select, and_, func, not_
from sqlalchemy.orm import sessionmaker

from app.keyboards.main_kb import keyboard_generator
from app.keyboards.register_kb import RegCallback, get_confirm, get_clusters_keyboard
from app.models.kazarma import KazarmaUser, KazarmaRole
from app.models.doc import User
from app.services.config import Config
from app.utils.states import Register

router = Router()
router.message.filter(F.chat.type == 'private')
router.callback_query.filter(F.message.chat.type == 'private')


@router.callback_query(RegCallback.filter(F.param == 'register'))
async def get_fullname(call: types.CallbackQuery, state: FSMContext):
    await call.message.delete()
    await call.message.answer('Напиши свое ФИО.\n\n<i>Например, Иванов Иван Иванович</i>.\n'
                              'Если передумаешь, напиши /start или "отмена".',
                              reply_markup=ForceReply(input_field_placeholder='Иванов Иван Иванович'))
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
    async with db_session() as session:
        temp_user = await session.execute(stmt)
        temp_users = temp_user.mappings().all()
        await session.commit()
    temp_users = [dict(user.items()) for user in temp_users]
    if not temp_users:
        await msg.answer('Я не нашел такого пользователя в "Инфоклинике".'
                         ' Пожалуйста, проверь, правильно ли ты заполнил имя.')
        return
    elif len(temp_users) > 1:
        await state.update_data(temp_users=temp_users)
        text = 'Я нашел в "Инфоклинике" следующие аккаунты:\n\n'
        for num, user in enumerate(temp_users, 1):
            text += f'<b>{num}. {user["fullname"]}</b>\nДолжность: {user["name"]}'
        text += '\n\nПожалуйста, выбери, какой из них верный'
        await msg.answer(text=text, reply_markup=await get_confirm(temp_users))
    else:
        await state.update_data(temp_users=temp_users[0])
        text = f'Нашел в "Инфоклинике" аккаунт:\n\n' \
               f'<b>{temp_users[0]["fullname"]}</b>' \
               f'\nДолжность: {temp_users[0]["name"]}' \
               f'\nЕсли я прав, пожалуйста, нажми кнопку подтверждения.'
        await msg.answer(text=text, reply_markup=await get_confirm(temp_users[0]))
    await state.set_state(Register.confirm)


@router.callback_query(RegCallback.filter(F.param == 'confirm'), Register.confirm)
async def get_cluster(call: types.CallbackQuery, state: FSMContext, db_session: sessionmaker,
                      callback_data: RegCallback):
    if callback_data.value == 0:
        with suppress(TelegramBadRequest):
            await call.message.edit_text('Тогда прошу тебя проверить ФИО и попробовать еще раз.', reply_markup=None)
        await state.set_state(Register.fullname)
        return
    user_data = await state.get_data()
    user_data: Union[list, dict] = user_data['temp_users']
    if isinstance(user_data, list):
        for data in user_data:
            if data['id'] == callback_data.value:
                user_data = data
                break
        await state.update_data(temp_users=user_data)
    if user_data['role_id'] in (5, 17, 29, 30):
        async with db_session() as session:
            result = await session.execute(select(User).filter(User.kazarma_id == user_data['role_id']))
            user = result.first()
            if user:
                with suppress(TelegramBadRequest):
                    await call.message.edit_text('Такой пользователь уже существует. '
                                                 'Напиши /start, чтобы начать заново',
                                                 reply_markup=None)
                await state.clear()
                await session.commit()
                return
            user = session.add(
                User(
                    id=call.from_user.id,
                    fullname=user_data['fullname'],
                    kazarma_id=user_data['id'],
                    role_id=user_data['role_id'],
                    role_name=user_data['name'],
                    cluster_id=18,
                    is_admin=True,
                )
            )

            await session.commit()
            await session.refresh(user)
        with suppress(TelegramBadRequest):
            await call.message.edit_text(f'Вы определены как администратор. '
                                         f'Добро пожаловать, {user_data["fullname"].split()[1]}',
                                         reply_markup=None)
        logger.opt(lazy=True).log(
            'REGISTRATION',
            f'User {user_data["fullname"]} completely registered as admin'
        )
    else:
        with suppress(TelegramBadRequest):
            await call.message.answer('Теперь выбери свою команду:',
                                      reply_markup=await get_clusters_keyboard(db_session))
        await state.set_state(Register.cluster)


@router.callback_query(Register.cluster, RegCallback.filter(F.param == "cluster"))
async def finish_registration(call: types.CallbackQuery, state: FSMContext, db_session: sessionmaker,
                              callback_data: RegCallback, bot: Bot, config: Config):
    raw_data = await state.get_data()
    user_data = raw_data['temp_users']
    is_checking = True if callback_data.value > 11 else False
    user = User(
        id=call.from_user.id,
        fullname=user_data['fullname'],
        kazarma_id=user_data['id'],
        role_id=user_data['role_id'],
        role_name=user_data['name'],
        cluster_id=callback_data.value,
        is_checking=is_checking
    )
    async with db_session() as session:
        await session.merge(user)
        await session.commit()
    with suppress(TelegramBadRequest):
        await call.message.edit_text(f'Добро пожаловать, {user_data["fullname"].split()[1]}!', reply_markup=None)
    if callback_data.value > 11:
        checking_group = await bot.get_chat(config.misc.checking_group)
        await call.message.answer('Твоя должность определена, как должность проверяющего.\n'
                                  'Клиентов и апелляции для проверки я отправляю в специальную группу, '
                                  'вступи в неё по этой ссылке:\n'
                                  f'👉 {checking_group.invite_link}',
                                  reply_markup=await keyboard_generator(user))
        logger.opt(lazy=True).log(
            'REGISTRATION',
            f'User {user_data["fullname"]} completely registered as checker user'
        )
    else:
        await call.message.answer('Ты - отправляющий.\n'
                                  'Что я умею:\n'
                                  'Нажми <b>"Отправить клиента ▶️"</b>, чтобы загрузить клиента, '
                                  'подходящего под условия, я помогу тебе в процессе загрузки\n'
                                  'Кнопка <b>"Отклоненные клиенты 🔻"</b> вернет тебе список отклоненных клиентов\n'
                                  'Кнопка <b>"Моя статистика 📊"</b> вернет тебе Excel-табличку со списком твоих клиентов '
                                  'и их текущими статусами', reply_markup=await keyboard_generator(user))
        logger.opt(lazy=True).log(
            'REGISTRATION',
            f'User {user_data["fullname"]} completely registered as common user'
        )
