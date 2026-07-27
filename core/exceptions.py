"""
core/exceptions.py — Exceções tipadas do sistema DTF MANAGER PRO.
Substitui strings de erro genéricas por exceções com significado.
"""


class DTFError(Exception):
    """Erro base do sistema DTF MANAGER PRO."""


class ConfigError(DTFError):
    """Falha ao carregar ou validar config_app.json."""


class FonteNaoEncontrada(DTFError):
    """Fonte tipográfica não encontrada no sistema."""


class PSDAusente(DTFError):
    """PSD não encontrado no caminho cadastrado para o modelo."""


class CamadaPSDNaoEncontrada(DTFError):
    """Camada de telefone cadastrada não foi encontrada no PSD (arquivo foi alterado)."""
    def __init__(self, camada: str, profissao: str):
        super().__init__(
            f"Camada '{camada}' não encontrada no PSD do modelo '{profissao}'.\n"
            f"O arquivo PSD pode ter sido alterado — recadastre o modelo em "
            f"Gerenciar Modelos.")
        self.camada    = camada
        self.profissao = profissao


class ModeloInvalido(DTFError):
    """Modelo sem camadas de telefone cadastradas ou PSD ausente."""


class DBError(DTFError):
    """Falha ao ler ou gravar no banco de dados local (dtf_pro.db)."""


class ImportacaoError(DTFError):
    """Falha ao importar planilha (Excel/CSV) de pedidos."""


class RenderError(DTFError):
    """Falha durante a renderização de uma arte."""
    def __init__(self, pedido_id, motivo: str):
        super().__init__(f"Erro ao renderizar pedido {pedido_id}: {motivo}")
        self.pedido_id = pedido_id
        self.motivo     = motivo


class ValidationError(DTFError):
    """Pedido com campos obrigatórios ausentes."""
    def __init__(self, pedido_id, campos: list[str]):
        super().__init__(
            f"Pedido {pedido_id} incompleto. Campos ausentes: {', '.join(campos)}")
        self.pedido_id = pedido_id
        self.campos     = campos


class ExportError(DTFError):
    """Falha ao salvar PNG, PDF ou relatório."""


class UpdateError(DTFError):
    """Falha no processo de atualização."""
