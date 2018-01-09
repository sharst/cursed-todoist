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

    def get_project_names(self, ids=[]):
        prjs = self.api.projects.all()

        if ids:
            prjs = [prj for prj in prjs
                    if prj.data['id'] in ids]

        names = [proj.data['name'] for proj
                 in prjs]
        return names


    def get_projects(self):
        return [proj.data for proj
                in self.api.projects.all()]

    def get_project_id(self, project_name):
        for proj in self.api.projects.all():
            if proj.data['name'] == project_name:
                return proj.data['id']

    def add_item(self, content, project=None, item_order=0, indent=1):
        if project is None:
            project_id = self.get_project_id("Inbox")
        elif isinstance(project, (str, unicode)):
            project_id = self.get_project_id(project)
        elif isinstance(project, int):
            project_id = project

        prj_items = self.get_items([project_id], checked=True, deleted=True)
        for item in prj_items:
            if item['item_order'] >= item_order:
                item.update(item_order=item['item_order']+1)

        self.api.items.add(content, project_id, item_order=item_order, indent=indent)
        self.api.commit()
        self.api.sync()

    def complete_item(self, task_id):
        self.api.items.complete([task_id])
        self.api.commit()

    def get_items(self, projects=None, checked=False, deleted=False,
                  archived=False):
        items = self.api.items.all()

        if projects is not None:
            if isinstance(projects[0], (str, unicode)):
                proj_ids = [self.get_project_id(project)
                            for project in projects]
            else:
                proj_ids = projects

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

    def get_all_parents(self, task):
        parents = [task]
        if 'parent_id' in task.data and task.data['parent_id'] is not None:
            parents.extend(self.get_all_parents(self.api.items.get_by_id(task.data['parent_id'])))
        return parents


    def get_all_children(self, task):
        project_items = self.get_items(projects=[task['project_id']])
        children = [task]

        while True:
            ids = [tsk['id'] for tsk in children]
            ret = [tsk for tsk in project_items
                   if (tsk['parent_id'] in ids and tsk not in children)]

            # If we have found no more children, abort
            if not ret:
                break

            children.extend(ret)

        return children

if __name__ == '__main__':
    td = TodoistAbstractor()
    items = td.api.items.all()
    item = [item for item in items if item['content'].find("mytestneu3") > -1][0]
    print "Got task " + item['content']
    children = td.get_all_children(item)
    print "It has the children " + repr([tsk['content'] for tsk in children])

