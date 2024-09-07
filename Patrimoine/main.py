from CalculerPatrimoine import Patrimoine


pat = Patrimoine()
argentCompteCourantInitial = pat.GetArgentCompteCourant()
argentLivretAInitial = pat.GetArgentLivretA()

pat.EvolutionDuPatrimoine("Compte Courant", argentCompteCourantInitial, "Bilan/Archives/Compte Chèques")
pat.EvolutionDuPatrimoine("Livret A", argentLivretAInitial, "Bilan/Archives/livret A")

pat.AfficherGraphiqueHistogrammeSuperpose("M")
pat.AfficherGraphiqueCoteACote("M")
pat.AfficheGraphiqueInteractif()