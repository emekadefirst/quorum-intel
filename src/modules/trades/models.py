from tortoise import fields

from src.common.base_model import BaseModel


class Trade(BaseModel):
    """Our record of a trade we instructed OANDA to open.

    This is append-only audit: we capture the quant+news context and LLM
    reasoning at the moment of decision, so we can review bad trades later.
    OANDA remains the source of truth for execution state (price, P&L).
    """

    account = fields.ForeignKeyField(
        "models.Account",
        related_name="trades",
        on_delete=fields.CASCADE,
    )

    # What was placed; `units` is positive, `side` determines sign
    pair = fields.CharField(max_length=16)
    side = fields.CharField(max_length=4)  # buy | sell
    units = fields.IntField()

    # OANDA references (populated on fill)
    oanda_order_id = fields.CharField(max_length=64, null=True)
    oanda_trade_id = fields.CharField(max_length=64, null=True)
    fill_price = fields.FloatField(null=True)
    take_profit = fields.FloatField(null=True)
    stop_loss = fields.FloatField(null=True)

    # Lifecycle: pending|open|closed|rejected|cancelled
    status = fields.CharField(max_length=16, default="pending")
    close_price = fields.FloatField(null=True)
    realized_pl = fields.FloatField(null=True)
    closed_at = fields.DatetimeField(null=True)

    # Decision context (JSON blobs so we can grow fields without migrations)
    quant_snapshot = fields.JSONField(null=True)
    news_snapshot = fields.JSONField(null=True)
    llm_reasoning = fields.TextField(null=True)
    source = fields.CharField(max_length=32, default="manual")  # manual|agent

    class Meta(BaseModel.Meta):
        table = "trades"
        indexes = ["account_id", "pair", "status"]
