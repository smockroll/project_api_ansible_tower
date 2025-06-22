import requests
import json
import urllib3 # Importa per disabilitare i warning

# Disabilita i warning di certificato non verificato (opzionale, ma utile)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- Dettagli dell'API protetta ---
API_URL = "https://ansible-aap.tiaky.local/api/v2/inventories/3/hosts/"
USERNAME = "tak0098" # Sostituisci
PASSWORD = "Almapark2025.05@fumy"   # Sostituisci

# --- Funzione per fare una richiesta API autenticata ---
def fetch_authenticated_data(url, username, password):
    print(f"Tentativo di scaricare dati da: {url} con autenticazione Basic.")
    try:
        # AGGIUNTO: verify=False per ignorare la verifica SSL
        response = requests.get(url, auth=(username, password), timeout=10, verify=False)

        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as http_err:
        if response.status_code == 401:
            print(f"Errore di autenticazione: {http_err}. Credenziali non valide.")
        elif response.status_code == 403:
            print(f"Errore di autorizzazione: {http_err}. Accesso negato per le credenziali fornite.")
        else:
            print(f"Errore HTTP generico: {http_err}. Stato: {response.status_code}")
    except requests.exceptions.ConnectionError as conn_err:
        print(f"Errore di connessione: {conn_err}. Controlla la tua connessione internet o il server API.")
    except requests.exceptions.Timeout as timeout_err:
        print(f"Timeout della richiesta dopo 10 secondi: {timeout_err}. Il server non ha risposto in tempo.")
    except requests.exceptions.RequestException as req_err:
        print(f"Errore generico durante la richiesta API: {req_err}")
    except json.JSONDecodeError:
        print(f"Errore: La risposta non è un JSON valido. Contenuto: {response.text[:200]}...")
    except Exception as e:
        print(f"Si è verificato un errore inatteso: {e}: {e}")
    return None

# --- Esempio di utilizzo ---
if __name__ == "__main__":
    print("Inizio automazione per scaricare dati da un'API autenticata.")

    data_from_api = fetch_authenticated_data(API_URL, USERNAME, PASSWORD)

    if data_from_api:
        print("\nDati scaricati con successo:")
        print(json.dumps(data_from_api, indent=4))
    else:
        print("Nessun dato è stato scaricato.")

    print("\nAutomazione completata.")