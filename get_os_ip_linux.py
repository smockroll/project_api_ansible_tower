import subprocess
import os
import json
from urllib.parse import urljoin

# --- Configurazione API e File ---
# L'URL base COMPLETO per il primo richiamo all'API
CURL_BASE_URL = 'https://ansible-aap.tiaky.local/api/v2/groups/8/all_hosts/'
# Estrai la base URL (protocollo + host) per ricostruire gli URL successivi
BASE_API_URL_ROOT = 'https://ansible-aap.tiaky.local'

USERNAME = "tak0098"

# Recupera la password dalla variabile d'ambiente PASSW
PASSWORD = os.getenv("PASSW")

OUTPUT_FOLDER = "dati_awx"
OUTPUT_FILENAME = os.path.join(OUTPUT_FOLDER, "ansible_hosts_linux_all_pages.csv")
DEBUG_FULL_JSON_FILENAME = os.path.join(OUTPUT_FOLDER, "raw_full_hosts_data_debug.json")  # File per il JSON aggregato

if not PASSWORD:
    print("Errore: La variabile d'ambiente 'PASSW' non è impostata. Impossibile procedere.")
    exit(1)


def fetch_all_hosts_data_from_awx_api(url, username, password, base_api_root):
    """
    Esegue il comando curl per recuperare tutti gli host da AWX, gestendo la paginazione.
    Restituisce una lista di dizionari Python contenenti i dati di tutti gli host.
    """
    all_hosts = []
    current_url = url
    page_counter = 0

    print(f"Inizio recupero dati host da AWX. URL iniziale: {url}")

    # Loop di paginazione: continua finché 'next' ha un URL valido
    while current_url:
        page_counter += 1
        print(f"Recupero Pagina {page_counter}: {current_url}")
        curl_command = (
            f"curl -k --user {username}:{password} \"{current_url}\""
        )

        try:
            # Esegue il comando curl per ottenere una singola pagina
            result = subprocess.run(
                curl_command,
                shell=True,
                capture_output=True,
                text=True,
                check=True
            )

            # Parsifica la risposta JSON della pagina corrente
            page_data = json.loads(result.stdout)

            # Aggiungi i risultati della pagina corrente alla lista totale
            all_hosts.extend(page_data.get('results', []))

            # Ottieni l'URL relativo della prossima pagina
            next_relative_url = page_data.get('next')

            if next_relative_url:
                # Ricostruisci l'URL completo usando urljoin
                current_url = urljoin(base_api_root, next_relative_url)
            else:
                current_url = None  # Nessun'altra pagina

        except subprocess.CalledProcessError as e:
            print(f"Errore nell'esecuzione di curl alla pagina {page_counter}:\nSTDERR: {e.stderr}\nSTDOUT: {e.stdout}")
            print(f"Codice di uscita: {e.returncode}")
            return None
        except json.JSONDecodeError as e:
            print(
                f"Errore di parsing JSON dalla pagina {page_counter}. Contenuto non valido:\n{result.stdout[:500]}...")
            print(f"Dettagli errore: {e}")
            return None
        except FileNotFoundError:
            print("Errore: Il comando 'curl' non è stato trovato. Assicurati che sia installato e nel PATH.")
            return None
        except Exception as e:
            print(f"Si è verificato un errore inatteso durante il recupero dei dati: {e}")
            return None

    print(f"Recupero dati completato. Totale pagine recuperate: {page_counter}.")
    return all_hosts


def process_and_format_to_csv(hosts_data):
    """
    Filtra la lista di host per 'ostype == "linux"', estrae nome e IP,
    e formatta i risultati in una stringa CSV.
    """
    linux_hosts_data = []

    for host in hosts_data:
        host_name = host.get('name')
        variables_string = host.get('variables', '')
        current_ostype = None
        current_ip = None  # Nuova variabile per l'IP

        if variables_string:
            try:
                variables_json = json.loads(variables_string)
                current_ostype = variables_json.get('ostype')
                current_ip = variables_json.get('ansible_host')  # Estrai ansible_host
            except json.JSONDecodeError:
                pass

                # Filtra per 'linux' (case-insensitive) e assicurati che sia una stringa
        # E assicurati che ci sia un IP
        if (current_ostype and isinstance(current_ostype, str) and current_ostype.lower() == "linux") and \
                (current_ip and isinstance(current_ip, str)):  # Assicurati che l'IP sia presente e sia una stringa
            linux_hosts_data.append([host_name, current_ostype, current_ip])  # Aggiungi l'IP alla lista

    return linux_hosts_data


if __name__ == "__main__":
    print("Inizio automazione per scaricare e salvare dati degli host Linux da AWX.")

    if not os.path.exists(OUTPUT_FOLDER):
        os.makedirs(OUTPUT_FOLDER)
        print(f"Creata la cartella di output: {OUTPUT_FOLDER}")

    # 1. Recupera TUTTI i dati host dall'API AWX (gestendo la paginazione)
    all_hosts_raw_data = fetch_all_hosts_data_from_awx_api(CURL_BASE_URL, USERNAME, PASSWORD, BASE_API_URL_ROOT)

    if all_hosts_raw_data:
        print(f"DEBUG: Recuperati {len(all_hosts_raw_data)} host totali da tutte le pagine.")

        try:
            with open(DEBUG_FULL_JSON_FILENAME, "w", encoding="utf-8") as f:
                json.dump(all_hosts_raw_data, f, indent=2)
            print(f"DEBUG: JSON aggregato di tutti gli host salvato in '{DEBUG_FULL_JSON_FILENAME}'.")
        except Exception as e:
            print(f"DEBUG: Errore durante il salvataggio del JSON aggregato: {e}")

        # 2. Processa (filtra) gli host recuperati in Python
        linux_hosts = process_and_format_to_csv(all_hosts_raw_data)

        if linux_hosts:
            count_found_hosts = len(linux_hosts)
            print(f"\nConteggio host Linux trovati e filtrati: {count_found_hosts}")

            try:
                # Header CSV aggiornato con 'ip_address'
                csv_lines = ["name,ostype,ip_address"]
                for host_data in linux_hosts:
                    # Estrai i tre valori
                    name = host_data[0]
                    ostype = host_data[1]
                    ip_address = host_data[2]  # Recupera l'IP

                    # Applica l'escape per il CSV (raddoppia le virgolette interne se ci sono)
                    name_escaped = f"\"{name.replace('\"', '\"\"')}\"" if "," in name or "\"" in name else name
                    ostype_escaped = f"\"{ostype.replace('\"', '\"\"')}\"" if "," in ostype or "\"" in ostype else ostype
                    ip_address_escaped = f"\"{ip_address.replace('\"', '\"\"')}\"" if "," in ip_address or "\"" in ip_address else ip_address

                    csv_lines.append(f"{name_escaped},{ostype_escaped},{ip_address_escaped}")  # Aggiungi IP alla riga

                csv_output_content = "\n".join(csv_lines)

                with open(OUTPUT_FILENAME, "w", encoding="utf-8") as f:
                    f.write(csv_output_content)
                print(f"Dati degli host Linux salvati con successo in '{OUTPUT_FILENAME}'")
            except Exception as e:
                print(f"Errore durante il salvataggio del file CSV: {e}")
        else:
            print("Nessun host Linux trovato dopo il filtraggio.")
            print("Conteggio host Linux trovati e filtrati: 0")
    else:
        print("Nessun dato host recuperato da AWX. Impossibile procedere.")
        print("Conteggio host Linux trovati e filtrati: 0")

    print("\nAutomazione completata.")