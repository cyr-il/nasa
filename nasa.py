import requests
import datetime
import tempfile
import os
import shutil
import re
from jinja2 import Environment, FileSystemLoader
from moviepy.video.io.ImageSequenceClip import ImageSequenceClip
from PIL import Image
from dotenv import load_dotenv
load_dotenv()


# Configuration
NASA_API_KEY = os.getenv("NASA_API_KEY")  
TEMPLATE_FILE = "home.html"
DETAIL_FILE = "photo_detail.html"
OUTPUT_HTML = "nasa_gallery.html"
OUTPUT_VIDEO = "nasa_video.mp4"
TARGET_SIZE = (1280, 720)

# Supprimer caractères non valides pour les fichiers HTML
def sanitize_filename(name):
    return re.sub(r'[^a-zA-Z0-9_-]', '_', name)

# Récupération des images depuis l'API NASA
def get_nasa_images(days=9):
    url = "https://api.nasa.gov/planetary/apod"
    today = datetime.date.today()

    params = {
        "api_key": NASA_API_KEY,
        "start_date": (today - datetime.timedelta(days=days)).isoformat()
    }

    response = requests.get(url, params=params)
    response.raise_for_status()
    return response.json()

# Téléchargement des images
def download_images(images_data):
    temp_dir = tempfile.mkdtemp()
    downloaded = []

    for i, item in enumerate(images_data):
        url = item.get("url")
        if not url or item.get("media_type") != "image":
            continue

        try:
            ext = os.path.splitext(url)[-1]
            if ext.lower() not in [".jpg", ".jpeg", ".png"]:
                print(f"Non pris en charge : {url}")
                continue

            response = requests.get(url, timeout=10)
            response.raise_for_status()

            filename = f"nasa_{i}{ext}"
            path = os.path.join(temp_dir, filename)

            with open(path, "wb") as f:
                f.write(response.content)

            downloaded.append({
                "title": item.get("title", f"NASA Image {i}"),
                "explanation": item.get("explanation", ""),
                "src": path
            })

        except Exception as e:
            print(f"Erreur téléchargement {url}: {e}")

    return downloaded

# Redimensionnement des images
def resize_images(images):
    resized = []

    for image in images:
        try:
            original_path = image["src"]
            with Image.open(original_path) as img:
                img = img.resize(TARGET_SIZE, Image.LANCZOS)

                filename = sanitize_filename(os.path.basename(original_path)) + "_resized.jpg"
                output_path = os.path.join("images", filename)
                os.makedirs("images", exist_ok=True)
                img.save(output_path)

                image["resized_path"] = output_path
                image["detail_link"] = f"details/{filename.replace('.jpg', '')}_detail.html"
                image["alt"] = image["title"]
                image["src"] = output_path.replace("\\", "/")  # Format web
                resized.append(image)

        except Exception as e:
            print(f"Erreur redimensionnement {original_path}: {e}")

    return resized

# Génération HTML de la galerie
def generate_html(images):
    env = Environment(loader=FileSystemLoader('.'))
    template = env.get_template(TEMPLATE_FILE)
    return template.render(images=images)

# Génération HTML de détail
def generate_detail_html(image):
    env = Environment(loader=FileSystemLoader('.'))
    template = env.get_template(DETAIL_FILE)
    return template.render(image=image)

# Création d'une page de détail par image
def generate_detail_pages(images):
    os.makedirs("details", exist_ok=True)

    for image in images:
        html = generate_detail_html(image)
        filename = os.path.basename(image["detail_link"])
        detail_path = os.path.join("details", filename)
        with open(detail_path, "w", encoding="utf-8") as f:
            f.write(html)

# Création de la vidéo
def create_video(image_paths):
    clip = ImageSequenceClip(image_paths, fps=1)
    clip.write_videofile(OUTPUT_VIDEO, codec="libx264", logger="bar")

# Nettoyage
def cleanup(paths):
    for p in paths:
        try:
            if os.path.exists(p):
                os.remove(p)
        except Exception as e:
            print(f"Erreur suppression {p}: {e}")

# MAIN
def main():
    try:
        nasa_data = get_nasa_images()
        downloaded_images = download_images(nasa_data)

        if not downloaded_images:
            print("Aucune image téléchargée")
            return

        resized_images = resize_images(downloaded_images)

        html = generate_html(resized_images)
        with open(OUTPUT_HTML, "w", encoding="utf-8") as f:
            f.write(html)

        generate_detail_pages(resized_images)

        create_video([img["resized_path"] for img in resized_images])

        print("✅ Galerie, pages de détail et vidéo générées avec succès.")

    except Exception as e:
        print(f"Erreur globale : {e}")

if __name__ == "__main__":
    main()
