from .modules.Patrimoine import Patrimoine

def GetPatrimoine():
    pat = Patrimoine()
    argentCompteCourantInitial = pat.GetArgentCompteCourant()
    argentLivretAInitial = pat.GetArgentLivretA()

    pat.EvolutionDuPatrimoine("Compte Courant", argentCompteCourantInitial, "Bilan/Archives/Compte Chèques")
    pat.EvolutionDuPatrimoine("Livret A", argentLivretAInitial, "Bilan/Archives/livret A")
    pat.EvolutionDuPatrimoineBourse("Bilan/Archives/Bourse/Portefeuille.json")

    # pat.AfficherGraphiqueHistogrammeSuperpose("M")
    # pat.AfficherGraphiqueCoteACote("M")
    pat.AfficheGraphiqueInteractif()
    pat.AfficheGraphiqueAeraPlot()