from pathlib import Path
import yaml
from typing import Dict, Any

class Validator:
    """Valida il file di configurazione delle stazioni"""
    
    REQUIRED_FIELDS = ['serial', 'ip', 'port', 'role']
    VALID_ROLES = ['master', 'rover']
    
    @staticmethod
    def validate_config(config_path: Path) -> bool:
        """
        Valida struttura e contenuto del file di configurazione.
        Solleva ValueError se invalido.
        """
        if not config_path.exists():
            raise FileNotFoundError(f"File di configurazione non trovato: {config_path}")
            
        try:
            with open(config_path, 'r') as f:
                data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ValueError(f"Errore parsing YAML: {e}")
            
        if not data or 'receivers' not in data:
            raise ValueError("Il file deve contenere la chiave 'receivers'")
            
        receivers = data.get('receivers', {})
        if not receivers:
            print("Warning: Lista ricevitori vuota")
            return True
            
        for name, rcv in receivers.items():
            if not isinstance(rcv, dict):
                raise ValueError(f"Formato errato per ricevitore '{name}'")
                
            # Check required fields
            for field in Validator.REQUIRED_FIELDS:
                if field not in rcv:
                    raise ValueError(f"Ricevitore '{name}' manca del campo obbligatorio '{field}'")
                    
            # Check types/values
            if rcv['role'] not in Validator.VALID_ROLES:
                raise ValueError(f"Ricevitore '{name}' ha ruolo non valido '{rcv['role']}'. Validi: {Validator.VALID_ROLES}")
                
            if not isinstance(rcv['port'], int):
                raise ValueError(f"Ricevitore '{name}' porta deve essere intero, trovato: {type(rcv['port'])}")

            if 'timeout' in rcv and not isinstance(rcv['timeout'], int):
                raise ValueError(f"Ricevitore '{name}' timeout deve essere intero, trovato: {type(rcv['timeout'])}")

        print(f"Configurazione valida: {len(receivers)} ricevitori trovati.")
        return True
