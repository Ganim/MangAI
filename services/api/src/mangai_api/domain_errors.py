class ProjectNotFoundError(Exception):
    def __init__(self, project_id: str) -> None:
        super().__init__(f"Project '{project_id}' was not found.")
        self.project_id = project_id


class ProjectPageNotFoundError(Exception):
    def __init__(self, project_id: str, page_id: str) -> None:
        super().__init__(f"Page '{page_id}' was not found in project '{project_id}'.")
        self.project_id = project_id
        self.page_id = page_id


class RegionNotFoundError(Exception):
    def __init__(self, page_id: str, region_id: str) -> None:
        super().__init__(f"Region '{region_id}' was not found in page '{page_id}'.")
        self.page_id = page_id
        self.region_id = region_id


class UploadValidationError(ValueError):
    pass
