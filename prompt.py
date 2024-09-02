



class PROMPT():

    def __init__(self, prompt_name):

        self.prompt_name = prompt_name

        if self.prompt_name in ['ehrchunk']:
            NotImplementedError
        elif self.prompt_name in ['findentity']:
            NotImplementedError
        elif self.prompt_name in ['findinfo']:
            NotImplementedError
        elif self.prompt_name in ['finddate']:
            NotImplementedError
            