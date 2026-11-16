
#The results the API returns per resume and cant be changed after its created (private info hehe)
class ResumeData:

    def __init__(self, filename, name, skills, experience_by_field, certificates_by_industry):
        #AI response are stored as copies, so changes outside this class can't alter the data
        self._filename = filename
        self._name = name
        self._skills = list(skills)
        self._experience_by_field = dict(experience_by_field)
        self._certificates_by_industry = {k: list(v) for k, v in certificates_by_industry.items()}

    @classmethod
    def from_dict(cls, data):
        #Builds a ResumeData from one resume entry in AI's reponse and is called until all resume are done
        return cls(
            filename=data["filename"],
            name=data["name"],
            skills=data["skills"],
            experience_by_field=data["experience_by_field"],
            certificates_by_industry=data["certificates_by_industry"],
        )

    #Read-only getters
    @property
    def filename(self):
        return self._filename

    @property
    def name(self):
        return self._name

    @property
    def skills(self):
        return list(self._skills)

    @property
    def experience_by_field(self):
        return dict(self._experience_by_field)

    @property
    def certificates_by_industry(self):
        return {k: list(v) for k, v in self._certificates_by_industry.items()}

    def __repr__(self):
        return f"ResumeData(filename={self._filename!r}, name={self._name!r})"
