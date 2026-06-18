"""NaviRAG agent package.

Import the compiled graph explicitly from ``agent_app.agent``. Keeping this
package initializer free of runtime imports avoids creating models, clients,
stores, or the graph when a utility module is imported.
"""
