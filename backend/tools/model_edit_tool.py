"""Chat tool — surgical profile update without rebuilding the shed."""

UPDATE_MEMBER_PROFILE_TOOL = {
    "type": "function",
    "function": {
        "name": "update_member_profile",
        "description": (
            "Change section profile on existing members in the current model. "
            "Use for HEA/HEB/IPE/RHS etc. changes. Never rebuilds the whole shed."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "profile": {
                    "type": "string",
                    "description": "Catalog designation e.g. HEA450, HEB320",
                },
                "scope": {
                    "type": "string",
                    "enum": [
                        "selection",
                        "element_type",
                        "frame",
                        "truss",
                        "pair",
                        "group",
                    ],
                    "description": (
                        "selection=this member only; element_type=all columns/purlins/etc.; "
                        "frame=all members on same portal frame line"
                    ),
                },
                "reference_element_id": {
                    "type": "string",
                    "description": "Member id from viewport selection (required unless in args)",
                },
            },
            "required": ["profile", "scope"],
        },
    },
}
