from app.brokers.base import OrderRequest, OrderSide, OrderType
from app.brokers.paper import PaperBroker


def test_market_order_fills_and_opens_position():
    pb = PaperBroker(equity=100_000, spread_frac=0.0, slippage_frac=0.0)
    pb.connect()
    pb.set_price("X", 100.0)
    order = pb.submit_order(OrderRequest("X", OrderSide.BUY, 10, OrderType.MARKET))
    assert order.status.value == "filled"
    assert len(pb.positions()) == 1
    assert pb.positions()[0].qty == 10


def test_idempotent_client_order_id():
    pb = PaperBroker()
    pb.connect()
    pb.set_price("X", 100.0)
    req = OrderRequest("X", OrderSide.BUY, 10, OrderType.MARKET, client_order_id="abc")
    o1 = pb.submit_order(req)
    o2 = pb.submit_order(req)
    assert o1.id == o2.id
    assert len(pb.positions()) == 1  # not doubled


def test_limit_order_rests_then_fills_on_touch():
    pb = PaperBroker(spread_frac=0.0, slippage_frac=0.0)
    pb.connect()
    pb.set_price("X", 100.0)
    o = pb.submit_order(OrderRequest("X", OrderSide.BUY, 5, OrderType.LIMIT, price=95.0))
    assert o.status.value == "submitted"
    pb.on_tick("X", 96.0)
    assert o.status.value == "submitted"   # not touched yet
    pb.on_tick("X", 95.0)
    assert pb.get_order(o.id).status.value == "filled"


def test_stop_loss_closes_position():
    pb = PaperBroker(spread_frac=0.0, slippage_frac=0.0)
    pb.connect()
    pb.set_price("X", 100.0)
    pb.submit_order(OrderRequest("X", OrderSide.BUY, 10, OrderType.MARKET,
                                 stop_loss=95.0, take_profit=110.0))
    pb.on_tick("X", 94.0)   # triggers stop
    assert len(pb.positions()) == 0
    assert pb.realized_pnl < 0


def test_market_order_rejected_without_price():
    pb = PaperBroker()
    pb.connect()
    o = pb.submit_order(OrderRequest("NOPRICE", OrderSide.BUY, 1, OrderType.MARKET))
    assert o.status.value == "rejected"
