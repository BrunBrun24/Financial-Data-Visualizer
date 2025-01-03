from modules.patrimoine import Patrimoine

if __name__ == "__main__":
    repertoireJson = "data/"
    pat = Patrimoine(repertoireJson)
    pat.PlotlyInteractive("Bilan/", "Patrimoine.html")