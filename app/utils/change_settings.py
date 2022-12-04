from app.services.config import Config


async def change_bot_settings(config: Config, args: str) -> str:

    args_list: list = args.lower().strip().split()
    setting: str = args_list[0]
    mode: str = args_list[1]

    if setting not in ("send_client", "send_appeal"):
        return f"Настройка <code>{setting}</code> не распознана."
    if mode not in ("on", "off"):
        return f"Не распознал новое значение настройки <code>{setting}</code>."

    if setting == "send_client":
        if mode == "on":
            config.misc.send_client = True
        elif mode == "off":
            config.misc.send_client = False
    elif setting == "send_appeal":
        if mode == "on":
            config.misc.send_appeal = True
        elif mode == "off":
            config.misc.send_appeal = False

    await save_settings(setting, mode)

    return f"✅ Настройки сохранены\n\n" \
           f"Текущие настройки:\n" \
           f"Отправка новых клиентов: <b>{'ВКЛ.' if config.misc.send_client else 'ВЫКЛ.'}</b>\n" \
           f"Подача обжалований: <b>{'ВКЛ.' if config.misc.send_appeal else 'ВЫКЛ.'}</b>\n"


async def save_settings(setting: str, mode: str):
    setting = setting.upper()
    mode = True if mode == "on" else False

    with open('.env', 'r') as readfile:
        settings = readfile.read()

    settings_list = settings.split('\n')
    old_setting = ''
    for param in settings_list:
        if param.startswith(setting):
            old_setting = param

    new_setting = f'{setting}={mode}'
    settings = settings.replace(old_setting, new_setting)

    with open('.env', 'w') as writefile:
        writefile.write(settings)
