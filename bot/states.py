from aiogram.fsm.state import State, StatesGroup


class AddProduct(StatesGroup):
    title = State()
    description = State()
    category = State()
    subcategory = State()
    optimization_type = State()
    game = State()
    price = State()
    badge = State()
    before_fps = State()
    after_fps = State()
    photo_path = State()
    screenshot_path = State()
    full_file_path = State()
    demo_file_path = State()
    is_extra = State()
    restore_file_path = State()
