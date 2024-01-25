from PIL import Image
from flask import Flask, send_file, render_template, request, redirect, url_for
import os
import sqlite3
from operator import itemgetter

app = Flask(__name__, static_url_path='/static')


IMAGES_FOLDER = '/home/xiejia/mysite/images_folder'

THUMBNAIL_FOLDER = 'thumbnails'  # Create a new folder for thumbnails

def get_subfolders():
    subfolders = [f for f in os.listdir(IMAGES_FOLDER) if os.path.isdir(os.path.join(IMAGES_FOLDER, f))]
    return subfolders

def get_full_folder_content(folder_path):
    return get_folder_content(folder_path)

def get_folder_content(folder_path):
    content = []
    for item in os.listdir(folder_path):
        item_path = os.path.join(folder_path, item)
        if os.path.isdir(item_path):
            subfolder_content = get_folder_content(item_path)
            if subfolder_content:  # Only add folders with content
                content.append({'name': item, 'type': 'folder', 'content': subfolder_content})
        elif is_image_file(item):
            content.append({'name': item, 'type': 'file', 'path': item_path})
    return content

def is_image_file(filename):
    # Add more file extensions as needed
    image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.tif'}
    _, extension = os.path.splitext(filename.lower())
    return extension in image_extensions

def get_image_filenames(folder):
    image_filenames = [f for f in os.listdir(os.path.join(IMAGES_FOLDER, folder)) if f.lower().endswith(('jpg', 'jpeg', 'png', 'tif', 'tiff'))]
    return image_filenames

def create_thumbnail(folder, filename):
    image_path = os.path.join(IMAGES_FOLDER, folder, filename)
    thumbnail_folder = os.path.join(THUMBNAIL_FOLDER, folder)

    # Create the thumbnails folder if it doesn't exist
    os.makedirs(thumbnail_folder, exist_ok=True)

    thumbnail_path = os.path.join(thumbnail_folder, f"{filename}_thumbnail.jpg")

    # Create a thumbnail (adjust the size as needed)
    with Image.open(image_path) as img:
        img.thumbnail((800, 640))
        img.save(thumbnail_path)

    return thumbnail_path


def get_image_metadata(folder, filename):
    # Connect to the database
    conn = sqlite3.connect('/home/xiejia/mysite/Image_metadata.db')
    cursor = conn.cursor()

    # Execute a query to fetch metadata
    query = "SELECT date, notes, keywords, fulltext FROM image_metadata WHERE folder = ? AND filename = ?"
    cursor.execute(query, (folder, filename))
    result = cursor.fetchone()

    # Close the database connection
    conn.close()

    # Return a dictionary with metadata
    metadata = {}

    if result:
        metadata = {
            'date': result[0],
            'notes': result[1],
            'keywords': result[2],
            'fulltext': result[3],
        }

    return metadata

def update_metadata_in_database(folder, filename, date, notes, keywords, fulltext):
    print(f"Updating metadata for {folder}/{filename}...")
    # Connect to the database
    conn = sqlite3.connect('Image_metadata.db')
    cursor = conn.cursor()

    # Check if metadata for the image already exists
    query_select = "SELECT * FROM image_metadata WHERE folder=? AND filename=?"
    cursor.execute(query_select, (folder, filename))
    existing_metadata = cursor.fetchone()
    filename_without_extension = os.path.splitext(filename)[0]

    if existing_metadata:
        # Metadata exists, update the existing row
        query_update = "UPDATE image_metadata SET date=?, notes=?, keywords=?, fulltext=? WHERE folder=? AND filename=?"
        cursor.execute(query_update, (date, notes, keywords, fulltext, folder, filename))
    else:
        # Metadata doesn't exist, insert a new row
        query_insert = "INSERT INTO image_metadata (folder, filename, date, notes, keywords, fulltext) VALUES (?, ?, ?, ?, ?, ?)"
        cursor.execute(query_insert, (folder, filename, date, notes, keywords, fulltext))

    # Commit the changes and close the connection
    conn.commit()
    conn.close()
    print("Metadata updated successfully!")

def perform_search_in_database(search_query, fields=None):
    with sqlite3.connect('/home/xiejia/mysite/Image_metadata.db') as conn:
        cursor = conn.cursor()
        if fields is None:
            fields = ["filename", "notes", "keywords", "fulltext"]  # Default to searching all fields
        where_clause = " OR ".join(f"{field} LIKE ?" for field in fields)
        query = f"SELECT * FROM image_metadata WHERE {where_clause}"
        params = ['%' + search_query + '%' for _ in fields]
        return cursor.execute(query, params).fetchall()

def update_text_file_content(folder, filename, fulltext):
    # Remove the ".jpg" extension from the filename
    filename_without_extension = os.path.splitext(filename)[0]

    text_file_path = os.path.join(IMAGES_FOLDER, folder, filename_without_extension + '.txt')

    # Write the fulltext content to the associated text file
    with open(text_file_path, 'w', encoding='utf-8') as text_file:
        text_file.write(fulltext)

# Add the Flask routes below this line

@app.route('/')
def index():
    subfolders = get_subfolders()
    subfolders.sort(reverse=True)  # Sort the list alphabetically
    return render_template('index.html', subfolders=subfolders)

@app.route('/view_folder/<path:folder>')
def view_folder(folder):
    folder_path = os.path.join(IMAGES_FOLDER, folder)
    folder_content = get_full_folder_content(folder_path)
         # Sort folder_content alphabetically by name
    folder_content = sorted(folder_content, key=itemgetter('name'))
    return render_template('view_folder.html', folder=folder, folder_content=folder_content)


@app.route('/image_info/<path:folder>/<filename>', methods=['GET', 'POST'])
def image_info(folder, filename):
    image_metadata = {}  # Initialize an empty dictionary

    if request.method == 'POST':
        # Handle any form submissions if needed
        pass

    # Fetch image metadata from the database if the request method is GET
    if request.method == 'GET':
        image_metadata = get_image_metadata(folder, filename)

    # Get the list of image filenames in alphabetical order
    image_filenames = get_image_filenames(folder)
    image_filenames.sort()

    # Find the index of the current filename
    current_index = image_filenames.index(filename)

    # Determine the previous and next filenames
    prev_filename = image_filenames[current_index - 1] if current_index > 0 else None
    next_filename = image_filenames[current_index + 1] if current_index < len(image_filenames) - 1 else None

    # Render the image_info.html template
    return render_template('image_info.html', folder=folder, filename=filename,
                           image_metadata=image_metadata, prev_filename=prev_filename, next_filename=next_filename)


@app.route('/view_image/<path:folder>/<filename>')
def view_image(folder, filename):
    image_path = os.path.join(IMAGES_FOLDER, folder, filename)
    # Determine MIME type based on file extension
    _, extension = os.path.splitext(filename.lower())
    mimetype = f'image/{extension[1:]}'  # Remove the leading dot in the extension
    return send_file(image_path, mimetype=mimetype)

@app.route('/thumbnail/<path:folder>/<filename>')
def thumbnail(folder, filename):
    thumbnail_path = create_thumbnail(folder, filename)
    # Determine MIME type based on file extension
    _, extension = os.path.splitext(filename.lower())
    mimetype = f'image/{extension[1:]}'  # Remove the leading dot in the extension
    return send_file(thumbnail_path, mimetype=mimetype)

@app.route('/add_metadata/<path:folder>/<filename>', methods=['GET', 'POST'])
def add_metadata(folder, filename):
    existing_metadata = get_image_metadata(folder, filename) or {}
    filename_without_extension = os.path.splitext(filename)[0]
    if request.method == 'POST':
        # Process the form data and save metadata to the database
        date = request.form['date']
        notes = request.form['notes']
        keywords = request.form['keywords']
        fulltext = request.form['fulltext']

        # Save metadata to the database
        update_metadata_in_database(folder, filename, date, notes, keywords, fulltext)

        # Update the associated text file with the fulltext content
        update_text_file_content(folder, filename, fulltext)

        # Redirect back to image_info after saving metadata
        return redirect(url_for('image_info', folder=folder, filename=filename))

    # Render the add_metadata.html template for GET requests
    return render_template('add_metadata.html', folder=folder, filename=filename, existing_metadata=existing_metadata)

@app.route('/save_metadata/<path:folder>/<filename>', methods=['POST'])
def save_metadata(folder, filename):
    print("Form submitted!oo")
    date = request.form.get('date')
    notes = request.form.get('notes')
    keywords = request.form.get('keywords')
    fulltext = request.form.get('fulltext')

    # Save metadata to the database (implement as needed)
    # Debug: Print extracted metadata
    # print(f"Date: {date}, Notes: {notes}, Keywords: {keywords}")
    # Update the database with the provided metadata
    update_metadata_in_database(folder, filename, date, notes, keywords, fulltext)

    # Update the associated text file with the fulltext content
    update_text_file_content(folder, filename, fulltext)

    # Redirect back to the image_info page after saving metadata
    return redirect(url_for('image_info', folder=folder, filename=filename))

@app.route('/search_images', methods=['GET'])
def search_images():
    # Get the search query and type from the URL parameters
    search_query = request.args.get('search', '')
    search_type = request.args.get('search_type', 'filename')

    # Define the fields based on the search type
    if search_type == 'filename':
        fields = ['filename']
    elif search_type == 'all':
        fields = ['filename', 'date', 'notes', 'keywords', 'fulltext']
    elif search_type == 'date':
        fields = ['date']
    elif search_type == 'fulltext':
        fields = ['fulltext']
    elif search_type == 'keywords':
        fields = ['keywords']
#    else:  # Both
#        fields = ['filename', 'date', 'notes', 'keywords', 'fulltext']

    # Perform a search in your database based on the search type
    search_results = perform_search_in_database(search_query, fields)

    # Render a template to display the search results
    return render_template('search_results.html', search_results=search_results, search_query=search_query, search_type=search_type)

@app.route('/about') #关于本站
def about():
    return render_template('about.html')


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)

