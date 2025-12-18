import multiprocessing
import signal
import sys
import time
from node_process import run_node
import subprocess
import os

def start_nodes(n=10, base_port=12000):
    procs = []
    for i in range(n):
        p = multiprocessing.Process(target=run_node, args=(i, base_port), daemon=True)
        p.start()
        procs.append(p)
    return procs

if __name__ == "__main__":
    multiprocessing.set_start_method('spawn')  # bezpieczne na Windows i Unix
    NUM_NODES = 10
    BASE_PORT = 12000

    # Start nodes
    procs = start_nodes(NUM_NODES, BASE_PORT)
    print("Uruchomiono procesy węzłów.")

    # Uruchom GUI
    try:
        from gui import run_gui
        run_gui()
    except Exception as e:
        print("Błąd GUI:", e)
    finally:
        print("Zamykanie procesów węzłów...")
        for p in procs:
            try:
                p.terminate()
            except:
                pass
        time.sleep(0.5)
        print("Zakończono.")
        sys.exit(0)
