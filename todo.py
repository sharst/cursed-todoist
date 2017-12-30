import todoist
import os

class TodoistAbstractor(object):
    def __init__(self):
        self.setup()

    def setup(self):
        with open(os.path.join(os.getenv('HOME') + '/.todoist'), 'r') as config:
            self.api = todoist.TodoistAPI(config.read().strip())

    def start_sync(self):
        self.api.sync()

    def get_project_names(self):
        return [proj.data['name'] for proj
                in self.api.projects.all()]

    def get_projects(self):
        return [proj.data for proj
                in self.api.projects.all()]

    def get_project_id(self, project_name):
        for proj in self.api.projects.all():
            if proj.data['name'] == project_name:
                return proj.data['id']

    def add_item(self, content, project=None):
        if project is None:
            project_id = self.get_project_id("Inbox")
        else:
            project_id = self.get_project_id(project)

        self.api.items.add(content, project_id)
        self.api.commit()

    def complete_item(self, task_id):
        self.api.items.complete([task_id])
        self.api.commit()

    def get_items(self, projects=None, checked=False, deleted=False,
                  archived=False):
        items = self.api.items.all()

        if projects is not None:
            proj_ids = [self.get_project_id(project)
                        for project in projects]

            items = [item for item in items
                     if item.data['project_id'] in proj_ids]

        if not checked:
            try:
                items = [item for item in items
                         if not item.data['checked']]
            except KeyError:
                pass

        if not deleted:
            try:
                items = [item for item in items
                         if not item.data['is_deleted']]
            except KeyError:
                pass

        if not archived:
            try:
                items = [item for item in items
                         if not item.data['is_archived']]
            except KeyError:
                pass

        return items

if __name__ == '__main__':
    td = TodoistAbstractor()
