from dataclasses import dataclass, asdict
import json


@dataclass
class ClientConfig:
    """Structured client-side configuration object.  Provides type safety
    and clear field definitions for server-to-client communication via
    template injected JS via context processor.  Consumed only by main.css.
    ALl other JS modules should look to main.css for relaying of these as
    needed.

    """
    DEBUG         : bool
    ENVIRONMENT   : str
    VERSION       : str
    TRIP_ID       : int
    
    def to_json_dict(self) -> dict:
        """
        Convert to dictionary suitable for JSON serialization in templates.
        Ensures proper JavaScript boolean/null handling.
        """
        return json.dumps({
            key: (value if value is not None else 'null')
            for key, value in asdict(self).items()
        }, indent=4 )
