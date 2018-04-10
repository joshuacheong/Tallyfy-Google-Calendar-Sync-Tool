from __future__ import print_function

import requests
import datetime

authDict = {}
authDict["password"] = "YOUR TALLYFY PASSWORD"
authDict["email"] = "YOUR TALLYFY EMAIL"
orgID = "YOUR ORGANIZATION ID"

reqAuth = requests.post('https://v2-api.tallyfy.com/auth/login', data=authDict)
if reqAuth.status_code == 200:
    print("Tallyfy API authorisation successful.")
else:
    print("\n\nTallyfy API authorisation failed: \nPlease make sure your username and password is correct. \nPlease also ensure your internet is working. \nIf not, Tallyfy API may be down.")

data = reqAuth.json()

accessHeader = {'Authorization': 'Bearer ' +
                data["data"]["token"]["access_token"]}

# responseString = json.dumps(data, indent=2)
# print(responseString)

url = 'https://v2-api.tallyfy.com/organizations/' + orgID + '/me/tasks'


def extractTasks(url, header, returnList):
    r = requests.get(url, headers=header)
    try:
        r.raise_for_status()
        print("Tallyfy API call for task extraction is successful.")
    except requests.exceptions.HTTPError as e:
        # Whoops it wasn't a 200
        return "\n\nTallyfy API call for task extraction failed:\n" + str(e)
    rData = r.json()["data"]
    for task in rData:
        deadline = task["deadline"]
        deadline = datetime.datetime.strptime(deadline, '%Y-%m-%dT%H:%M:%SZ')
        # Check if the task is part of a process
        if task["run_id"] is None:
            returnList.append({
                'id': str(task["id"]),
                'summary': str(task["name"]),
                'description': str(task["description"]),
                'start': {
                    'date': str(deadline.date()),
                },
                'end': {
                    'date': str(deadline.date()),
                },
                'reminders': {
                    'useDefault': True,
                },
                'colorId': '10', })
        else:
            returnList.append({
                'id': str(task["id"]),
                'summary': str(task["step"]["title"]),
                'description': str(task["step"]["summary"]),
                'start': {
                    'date': str(deadline.date()),
                },
                'end': {
                    'date': str(deadline.date()),
                },
                'reminders': {
                    'useDefault': True,
                },
                'colorId': '10', })
    try:
        nextURL = r["meta"]["pagination"]["links"]["next"]
        extractTasks(nextURL, header, returnList)
    except TypeError as e:
        # This ends the function when no more tasks are found as nextURL does not exist.
        return
