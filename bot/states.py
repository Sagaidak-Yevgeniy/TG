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
    photo = State()
    screenshot = State()
    full_link = State()
    demo_link = State()
    is_extra = State()
    restore_link = State()


class PromoCreate(StatesGroup):
    code = State()
    discount_percent = State()
    expires_at = State()
    usage_limit = State()


class PromoApply(StatesGroup):
    code = State()


class ReviewCreate(StatesGroup):
    rating = State()
    comment = State()


class SectionPhotoEdit(StatesGroup):
    photo = State()
