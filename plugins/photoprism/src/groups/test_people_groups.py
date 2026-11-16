import json
import tempfile
import unittest
from pathlib import Path

import people_groups


class PeopleGroupsTest(unittest.TestCase):
    def test_or_query(self) -> None:
        query = people_groups.person_search_query(["Mario Rossi", "Luca Bianchi", "Anna Verdi"])
        self.assertEqual(query, 'person:"Mario Rossi|Luca Bianchi|Anna Verdi"')

    def test_two_members_enough(self) -> None:
        markers = [
            {"SubjUID": "a", "Name": "Mario Rossi", "Invalid": False},
            {"SubjUID": "b", "Name": "Luca Bianchi", "Invalid": False},
            {"SubjUID": "z", "Name": "Altro", "Invalid": False},
        ]
        hits = people_groups.group_member_hits(
            markers, {"a", "b", "c"}, {"Mario Rossi", "Luca Bianchi", "Anna Verdi"}
        )
        self.assertEqual(len(hits), 2)

    def test_inject_once(self) -> None:
        html = b"<html><body>x</body></html>"
        out = people_groups.inject_nav(html, "text/html; charset=utf-8")
        self.assertIn(b'id="homelab-people-groups-btn"', out)
        out2 = people_groups.inject_nav(out, "text/html")
        self.assertEqual(out2, out)

    def test_people_from_subjects(self) -> None:
        people = people_groups._people_from_subjects(
            [{"UID": "a", "Name": "Mario Rossi", "Type": "person"}]
        )
        self.assertEqual(people, [{"uid": "a", "name": "Mario Rossi"}])

    def test_inject_has_burger(self) -> None:
        html = b"<html><body>x</body></html>"
        out = people_groups.inject_nav(html, "text/html")
        self.assertIn(b"homelab-person-burger", out)
        self.assertIn(b"/__hub/people-groups/api/membership", out)

    def test_set_person_groups_create_and_multi(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            people_groups.GROUPS_PATH = Path(tmp) / "people-groups.json"
            people_groups.save_groups(
                [
                    {
                        "id": "g1",
                        "name": "Universita",
                        "personUids": [],
                        "personNames": [],
                    }
                ]
            )
            out = people_groups.set_person_groups("uidA", "Io", ["g1"], create_name="Famiglia")
            names = {group["name"]: group for group in out}
            self.assertIn("uidA", names["Universita"]["personUids"])
            self.assertIn("uidA", names["Famiglia"]["personUids"])
            self.assertEqual(names["Famiglia"]["personNames"], ["Io"])
            out2 = people_groups.set_person_groups("uidA", "Io", ["g1"], create_name="")
            names2 = {group["name"]: group for group in out2}
            self.assertIn("uidA", names2["Universita"]["personUids"])
            self.assertNotIn("uidA", names2["Famiglia"]["personUids"])

    def test_dispatch_lists_saved_group(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            people_groups.GROUPS_PATH = Path(tmp) / "people-groups.json"
            people_groups.save_groups(
                [{"id": "g1", "name": "Liceo", "personUids": ["u"], "personNames": ["Io"]}]
            )
            status, content_type, body = people_groups.dispatch("GET", "/__hub/people-groups/api/groups", "", b"", lambda *_a: (200, []))
            self.assertEqual(status, 200)
            self.assertIn("application/json", content_type)
            self.assertEqual(json.loads(body)["groups"][0]["name"], "Liceo")


if __name__ == "__main__":
    unittest.main()
