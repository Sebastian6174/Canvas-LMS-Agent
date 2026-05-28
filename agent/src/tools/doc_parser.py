import os.path
from google.oauth2 import service_account
from googleapiclient.discovery import build
from config import config

SCOPES = ['https://www.googleapis.com/auth/documents.readonly', 'https://www.googleapis.com/auth/drive.readonly']

def get_credentials():
    """Gets valid service account credentials from credentials.json."""

    if not os.path.exists(config.credentials_path):
        raise FileNotFoundError(f"Missing credentials.json at {config.credentials_path}. Please follow the Google Docs API guide to get a Service Account JSON file.")

    # Se inicializan las credenciales
    creds = service_account.Credentials.from_service_account_file(
        config.credentials_path, scopes=SCOPES)
    
    return creds

def wrap_content(title, content):
    full_text = []
    
    for element in content:
        if 'paragraph' in element:
            for run in element['paragraph']['elements']:
                if 'textRun' in run:
                    full_text.append(run['textRun']['content'])
        
        elif 'table' in element:
            for row in element['table']['tableRows']:
                row_text = []
                for cell in row['tableCells']:
                    cell_content = []
                    for cell_element in cell['content']:
                        if 'paragraph' in cell_element:
                            for run in cell_element['paragraph']['elements']:
                                if 'textRun' in run:
                                    # Se eliminan los espacios extra dentro de las celdas pero se mantiene algo de estructura
                                    text = run['textRun']['content'].strip()
                                    if text:
                                        cell_content.append(text)
                    row_text.append(" ".join(cell_content))
                full_text.append("| " + " | ".join(row_text) + " |\n")
                    
    return {"title": title,
            "content": "".join(full_text)}

    
def read_google_doc(doc_id):
    """
    Lee un documento de Google y extrae su contenido de texto, incluyendo tablas.
    """
    try:
        full_document = []
        
        creds = get_credentials()
        service = build('docs', 'v1', credentials=creds)
        
        # Se obtiene el documento por su ID
        try:
            doc = service.documents().get(documentId=doc_id, includeTabsContent=True).execute()
        except Exception as api_err:
            if "Office file" in str(api_err):
                print(f"El documento {doc_id} es un archivo de Office. Intentando exportar usando Drive API...")
                try:
                    drive_service = build('drive', 'v3', credentials=creds)
                    request = drive_service.files().export_media(fileId=doc_id, mimeType='text/plain')
                    content_bytes = request.execute()
                    content = content_bytes.decode('utf-8', errors='replace')
                    return [{"title": "Documento Exportado", "content": content}]
                except Exception as export_err:
                    print(f"Advertencia: No se pudo exportar el archivo de Office (probablemente porque no es un documento de Google Docs nativo). Se omitirá la lectura de este documento. Detalles: {export_err}")
                    return None
            else:
                raise api_err
        
        print(f"--- Document Title: {doc.get('title')} ---")
                
        def process_tabs(tabs_list):
            results = []
            for tab in tabs_list:
                title = tab.get('tabProperties', {}).get('title', 'Untitled Tab')
                # Se extrae el contenido de la pestaña y se añade 
                if 'documentTab' in tab:
                    body = tab['documentTab'].get('body', {})
                    content = body.get('content', [])
                    results.append(wrap_content(title, content))
                
                # Se procesan recursivamente las pestañas anidadas si existen
                child_tabs = tab.get('childTabs')
                if child_tabs:
                    results.extend(process_tabs(child_tabs))
            return results

        tabs = doc.get('tabs')
        
        if tabs:
            full_document = process_tabs(tabs)
        else:
            # El documento no tiene pestañas (formato antiguo o simple)
            title = doc.get('title', 'Main Document')
            body = doc.get('body', {})
            content = body.get('content', [])
            full_document.append(wrap_content(title, content))
        
        return full_document


    except Exception as err:
        print(f"An error occurred: {err}")
        return None

