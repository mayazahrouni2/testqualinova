from sentence_transformers import SentenceTransformer
import warnings
warnings.filterwarnings('ignore')

print("📥 Démarrage du téléchargement optimisé du modèle BAAI/bge-m3...")
print("Cette opération peut prendre quelques minutes selon votre connexion.")
try:
    # Le téléchargement utilise maintenant hf_xet pour plus de vitesse et de fiabilité
    model = SentenceTransformer("BAAI/bge-m3")
    print("\n✅ MODÈLE TÉLÉCHARGÉ AVEC SUCCÈS ! Vous pouvez relancer Streamlit.")
except Exception as e:
    print(f"\n❌ Erreur rencontrée : {e}")
