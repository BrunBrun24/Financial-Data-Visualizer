from .modules.Patrimoine import Patrimoine
from .modules.TradeRepublicPerformance import TradeRepublicPerformance


def GetPatrimoine():
    # bourse = TradeRepublicPerformance("Bilan/Archives/Bourse/Transactions.json")
    # bourse.EnregistrerDataFrameEnJson("Bilan/Archives/Bourse/Portefeuille.json")

    pat = Patrimoine()
    pat.GraphiqueLineaireEvolutionPatrimoine()
    pat.GraphiqueLineaireAera()