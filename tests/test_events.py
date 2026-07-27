from domain.enums import EstadoPedido
from domain.events import EventBus, TipoEvento
import core.logger as log


def test_pedido_estado_publica_sem_mensagem():
    """Sem mensagem de proposito -- assim o LogArea (so renderiza eventos com
    mensagem) ignora esse evento automaticamente, sem precisar de filtro."""
    EventBus.get().reset()
    recebidos = []
    EventBus.get().subscribe(TipoEvento.PEDIDO_ESTADO_MUDOU, recebidos.append)

    log.pedido_estado(42, EstadoPedido.RENDERIZANDO)

    assert len(recebidos) == 1
    ev = recebidos[0]
    assert ev.mensagem == ""
    assert ev.dados == (42, EstadoPedido.RENDERIZANDO)
    EventBus.get().reset()
