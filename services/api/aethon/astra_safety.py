from app.security import SafetyKernel


class ASTRASafety:
    """ASTRA facade over AETHON's canonical safety kernel."""

    def __init__(self, kernel=None):
        self.kernel = kernel or SafetyKernel()

    def decide(self, risk, *, side_effects=False):
        return self.kernel.authorize(risk, side_effects)
