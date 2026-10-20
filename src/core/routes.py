from src.modules.account.routes import router as account_router
from src.modules.chat.routes import router as chat_router
from src.modules.news.routes import router as news_router
from src.modules.signals.routes import router as signals_router
from src.modules.trades.routes import router as trades_router
from src.modules.web.routes import router as web_router

routes = [
    account_router,
    signals_router,
    news_router,
    trades_router,
    chat_router,
    web_router,
]
