import os
import hashlib

class PrePromptIntegrityError(Exception):
    pass

class PrePromptHandler:
    
    PP_INTEGRITY = 'c95fa29d557d014faa83f232a1df62633e1d6d4a0dbf0348e16088de80dbadad'
    PP_FNAME = 'PP000001_20250722.txt'

    def __init__(self):
        pass

    def _get_pre_prompt_path(self):
        dirname = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(dirname, self.PP_FNAME)

    def _calc_pre_prompt_sha256(self, file_path):
        sha = hashlib.sha256()
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    sha.update(chunk)
            return sha.hexdigest()
        except FileNotFoundError:
            raise PrePromptIntegrityError(f"Error: File not found at {file_path}")
        except Exception as e:
            raise PrePromptIntegrityError(f"An error occurred while calculating SHA256 for {file_path}: {e}")

    def _verify_pre_prompt_integrity(self):
        file_path = self._get_pre_prompt_path()
        calculated_sha = self._calc_pre_prompt_sha256(file_path)

        if calculated_sha is None:
            raise PrePromptIntegrityError("Could not calculate file SHA256. Integrity check failed.")

        if calculated_sha == self.PP_INTEGRITY:
            return True
        else:
            return False
        
    def get_pre_prompt(self):
        
        pp_validated = self._verify_pre_prompt_integrity()
        
        if not pp_validated:
            raise PrePromptIntegrityError("Could not validate the integritiy of the pre-prompt file.")
        
        file_path = self._get_pre_prompt_path()

        actual_hash = self._calc_pre_prompt_sha256(file_path)
        if actual_hash != self.PP_INTEGRITY:
            raise PrePromptIntegrityError("Could not calculate file SHA256. Integrity check failed.")

        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()