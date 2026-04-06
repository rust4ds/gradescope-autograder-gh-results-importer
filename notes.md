
**testing methodology:**
-> build test cases from current homework
-> build into this autograder format

-> **github action**
    -> not necessarily triggerable by students (if it is then it sends directly to gradescope which is fine i guess???)
    -> returns student facing grade
    -> also exports to gradescope (or some bucket), gh action will export to api?
    -> points for commit count
    -> points for branch count (can copy directly from repo)
    -> late: pull deadlines from yaml file with the tests
    -> workflow protection

-> **gradescope autograder**
    -> pulls json file? from where? where does it store and export? how do we authenticate?? (maybe s3 bucket?)
    -> reflects accordingly into gradescope

WHERE SHOULD I PUT THE EVERYTHING FILE?? -> want to make everything as universal as possible to upload
-> commit count constraints
-> branch count constraints
-> test code
-> expected answers for the normal running tests
-> deadlines

how do we know who's assignment is whos?

ultimate goal:
-> rpc post/webapp/email asks for upload the "everything file"
    -> includes list of github and corresponding email
-> when user runs action in github classroom, action runs, autogrades everything that needs to be done and exports to json file. this json file can't be spoofed (none of this needs to be added to a .autograder file, solely gh action). has access to the everything file, and saves to bucket accordingly. (exports hash as a part of the post)
-> gradescope has hash as well, pulls the data since it knows who the person is (theoretically?). although core grade needs to be represented on gradescope, how could we get students to upload something on both gradescope and on github for the homework? maybe a reflection?
    -> pulls data from same bucket with the json, uses that for the autograder

-> also could just do an autograder via gradescope upload github