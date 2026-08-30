"""
mod_communication.py
Communication Siemens S7 <-> Python avec python-snap7.

Ce module :
- gere la connexion/deconnexion au PLC ;
- lit le DB620 ;
- decode les BOOL/INT utiles ;
- renvoie un dictionnaire propre au dashboard ;
- gere les erreurs sans faire planter l'IHM.

Pour le PLC virtuel :
    PLC_IP = "172.21.1.10"

Pour le vrai S7-1200 :
    modifier PLC_IP avec l'adresse du PLC.

CORRECTIONS APPORTEES (voir rapport d'audit) :
- Le parametre `timeout_ms` etait stocke mais jamais applique au client
  Snap7. Un PLC injoignable pouvait donc bloquer connect()/db_read()
  pendant de tres longues periodes (observees jusqu'a ~60 s selon la
  configuration reseau). Il est maintenant applique via
  `client.set_param(...)` juste apres la creation du client.
- En cas d'echec de lecture, le socket applicatif est desormais
  explicitement ferme (disconnect) avant la prochaine tentative de
  connexion, pour eviter un etat "zombie" ou get_connected() renverrait
  un etat incoherent.
- Remplacement du "magic number" 24 par la constante DB_SIZE.
- Ajout d'un support "context manager" (with PLCConnector(...) as plc).
- Ajout de logs (module logging) a la place de print() pur, pour une
  integration propre avec un systeme de supervision de logs.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import snap7
from snap7.type import Parameter
from snap7.util import get_bool, get_int

logger = logging.getLogger(__name__)


class PLCConnector:
    """Client Snap7 simple et robuste pour le DB620."""

    DB_NUMBER = 620
    DB_SIZE = 24

    def __init__(
        self,
        ip: str = "172.21.1.10",
        rack: int = 0,
        slot: int = 1,
        timeout_ms: int = 1500,
    ) -> None:
        self.ip = ip
        self.rack = rack
        self.slot = slot
        self.timeout_ms = timeout_ms

        self.client = snap7.client.Client()
        self._apply_timeouts()

        self.connected = False
        self.last_error = ""
        self.last_data: Optional[bytes] = None

    # ------------------------------------------------------------------
    # Configuration bas niveau
    # ------------------------------------------------------------------
    def _apply_timeouts(self) -> None:
        """Applique le timeout configure au client Snap7.

        Sans cela, un PLC injoignable (mauvaise IP, cable debranche...)
        peut faire bloquer connect() pendant de tres longues periodes
        (comportement par defaut de la pile ISO-TCP de Snap7).
        """
        for parameter in (Parameter.PingTimeout, Parameter.SendTimeout, Parameter.RecvTimeout):
            try:
                self.client.set_param(parameter, int(self.timeout_ms))
            except Exception as exc:  # pragma: no cover - depend de la version snap7
                logger.debug("Impossible de definir %s: %s", parameter, exc)

    # ------------------------------------------------------------------
    # Connexion
    # ------------------------------------------------------------------
    def connect(self) -> bool:
        """Connecte le client au PLC et retourne True si OK."""
        self.last_error = ""

        try:
            if self.client.get_connected():
                self.connected = True
                return True
        except Exception:
            pass

        try:
            self.client.connect(self.ip, self.rack, self.slot)
            self.connected = bool(self.client.get_connected())

            if not self.connected:
                self.last_error = "Connexion Snap7 non etablie."

            return self.connected

        except Exception as exc:
            self.connected = False
            self.last_error = str(exc)
            logger.warning("Echec de connexion au PLC %s: %s", self.ip, exc)
            # On force un etat propre du client pour que la prochaine
            # tentative reparte sur une base saine.
            self._safe_disconnect()

            # Certaines versions de python-snap7 laissent l'objet Client
            # dans un etat interne incoherent apres une exception levee
            # PENDANT connect()/get_connected() (ex: TypeError du type
            # "'bytes' object does not support item assignment", qui vient
            # de la librairie snap7 elle-meme, pas de ce module). Dans ce
            # cas, se contenter de disconnect() ne suffit pas toujours :
            # on recree un client Snap7 tout neuf pour repartir sur une
            # base saine au prochain essai.
            if isinstance(exc, TypeError):
                logger.warning(
                    "Etat interne Snap7 incoherent detecte, reinitialisation du client."
                )
                try:
                    self.client = snap7.client.Client()
                    self._apply_timeouts()
                except Exception as reinit_exc:  # pragma: no cover
                    logger.error("Echec de reinitialisation du client Snap7: %s", reinit_exc)

            return False

    def disconnect(self) -> None:
        """Ferme proprement la connexion."""
        self._safe_disconnect()
        self.connected = False

    def _safe_disconnect(self) -> None:
        try:
            if self.client.get_connected():
                self.client.disconnect()
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Lecture DB
    # ------------------------------------------------------------------
    def read_raw_db(
        self,
        db_number: int | None = None,
        size: int | None = None,
        start: int = 0,
    ) -> Optional[bytes]:
        """Lit les octets bruts d'un DB a partir de n'importe quel offset.

        Args:
            db_number: numero du DB (par defaut self.DB_NUMBER).
            size: nombre d'octets a lire (par defaut self.DB_SIZE).
            start: offset de depart en octets dans le DB (0 par defaut).
        """
        db_number = self.DB_NUMBER if db_number is None else db_number
        size = self.DB_SIZE if size is None else size

        if not self.connected and not self.connect():
            return None

        try:
            data = self.client.db_read(db_number, start, size)
            self.last_data = bytes(data)
            self.last_error = ""
            return self.last_data
        except Exception as exc:
            self.last_error = str(exc)
            self.connected = False
            # Le socket peut etre dans un etat incoherent (coupure reseau,
            # PLC redemarre, etc.) : on le referme explicitement pour que
            # connect() reparte sur une reconnexion complete plutot que de
            # boucler indefiniment sur un socket mort.
            self._safe_disconnect()
            logger.warning("Echec de lecture DB%s: %s", db_number, exc)
            return None

    # ------------------------------------------------------------------
    # Decode DB620
    # ------------------------------------------------------------------
    @staticmethod
    def decode_db620(data: bytes | bytearray) -> Dict[str, Any]:
        """Decode la structure utilisee par plc_simulator.py."""
        if data is None or len(data) < PLCConnector.DB_SIZE:
            raise ValueError(
                f"DB620 incomplet : {PLCConnector.DB_SIZE} octets sont necessaires."
            )

        
        b = bytearray(data)


        variables: Dict[str, Any] = {
            # Byte 0
            "loading_passed": get_bool(b, 0, 0),
            "unloading_passed": get_bool(b, 0, 1),
            "loading_failed": get_bool(b, 0, 2),
            "unloading_failed": get_bool(b, 0, 3),
            "clip_station_working": get_bool(b, 0, 4),
            "tape_station_working": get_bool(b, 0, 5),
            "table_running": get_bool(b, 0, 6),
            "tape_robot_state": get_bool(b, 0, 7),
            # Byte 1
            "clip_robot_state": get_bool(b, 1, 0),
            "small_robot_state": get_bool(b, 1, 1),
            "e_stop": get_bool(b, 1, 3),
            "table_service": get_bool(b, 1, 4),
            "table_auto": get_bool(b, 1, 5),
            "tape_service": get_bool(b, 1, 6),
            "tape_auto": get_bool(b, 1, 7),
            # Byte 2
            "clip_service": get_bool(b, 2, 0),
            "clip_auto": get_bool(b, 2, 1),
        }

        # Tapes / cassettes : 10 INT stockes aux offsets 4,6,...,22
        tape_states: List[int] = []
        for offset in range(4, 24, 2):
            tape_states.append(get_int(b, offset))
        variables["tape_states"] = tape_states

        # Metadonnees utiles pour le debug / diagnostic
        variables["db_number"] = PLCConnector.DB_NUMBER
        variables["db_size"] = len(b)

        return variables

    def read_variables(self) -> Optional[Dict[str, Any]]:
        """Lit et decode directement le DB620."""
        data = self.read_raw_db(self.DB_NUMBER, self.DB_SIZE)
        if data is None:
            return None

        try:
            return self.decode_db620(data)
        except Exception as exc:
            self.last_error = str(exc)
            logger.error("Echec de decodage DB620: %s", exc)
            return None

    # ------------------------------------------------------------------
    # Helpers diagnostic
    # ------------------------------------------------------------------
    def get_connection_info(self) -> Dict[str, Any]:
        return {
            "ip": self.ip,
            "rack": self.rack,
            "slot": self.slot,
            "db": self.DB_NUMBER,
            "size": self.DB_SIZE,
            "connected": self.connected,
            "error": self.last_error,
        }

    # ------------------------------------------------------------------
    # Context manager
    # ------------------------------------------------------------------
    def __enter__(self) -> "PLCConnector":
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.disconnect()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # Petit test console independant de PyQt.
    with PLCConnector(ip="172.21.1.10", rack=0, slot=1) as plc:

        print("===============================================")
        print(" TEST COMMUNICATION S7 - DB620")
        print("===============================================")
        print(f"PLC : {plc.ip} | Rack={plc.rack} | Slot={plc.slot}")

        if not plc.connected:
            print(f"ERREUR : {plc.last_error}")
        else:
            print("Connexion OK")
            values = plc.read_variables()
            if values is None:
                print(f"ERREUR LECTURE : {plc.last_error}")
            else:
                for key, value in values.items():
                    print(f"{key:24s} = {value}")