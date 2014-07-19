#!/usr/bin/env python
# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4
"""  software_inventory_vulnerability_check search a list of program
package names and versions in the NVD database.

depends on vfeed database, and a package inventory list
depends on list being in name or name:version format, 1 per line

author: Mark Menkhus
This is a RedCup research group project
menkhus@icloud.com

All rights reserved.

Copyright 2014 Mark Menkhus, RedCup Research Group

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.
"""

__version__ = '0.1'
__author__ = 'Mark Menkhus, menkhus@icloud.com'

class packageList():
    """ return a list of packages to get tested.
        input: filename where the content is a packagenames
        one per line, comments with # sign
    """
    def __init__ (self, packageFile='testlist.txt'):
        """ get a file name when object is instantiated
        """
        self.packageFile = packageFile
        self.packageList = []
    def getList (self):
        """ getList is a generator, it gets the data from the file 
            and yields the data as needed
        """
        import re
        try:
            self.packageListInput = open (self.packageFile, 'r').readlines() 
        except Exception, e:
            print "packageList: Exception - %s"%(e,)
            exit(1)
        for each in self.packageListInput:
            if re.search(r'^#', each):
                pass
            else:
                each = each.strip('\n')
                if each != '':
                    self.packageList.append(each)
                    yield each

class checknvd_by_package():
    """ Check a package string for existence in the nvd cpe data
        data string is 'packagename:version'
        depends on the vfeed.db database from the vfeed application
    """
    def __init__ (self, package=None, database='vfeed.db', items=10):
        """ Setup class 
        """
        self.package = package 
        self.database = database
        self.items = items
    def get_data(self):
        """   Get the data from the database.
        todo add the CVSS scores
        """
        try:
            import sqlite3
            self.conn = sqlite3.connect(self.database)
            self.cursor = self.conn.cursor()
        except Exception, e:
            print "checknvd_by_package.getdata: %s"%(e,)
            exit()
        self.sql = r"""SELECT DISTINCT c.cveid, n.cvss_base, c.cpeid, n.date_published, n.summary
        FROM nvd_db as n
        JOIN cve_cpe as c
        WHERE c.cpeid
        """
        self.sql += r' LIKE "%:' + self.package + r'"'
        self.sql += r' and c.cveid = n.cveid '
        self.sql += r'ORDER BY n.date_published DESC'
        #self.sql += r'LIMIT ' + str(self.items) + ';'
        self.sql += r';'
        self.data = self.cursor.execute(self.sql)
        if self.data != None:
            self.data = self.data.fetchall()
            self.conn.close()
            return self.data
        else:
            return None
    def __str__(self):
        self.s = ''
        if len(self.data) > 0:
                self.s = "*** Potential security defect found in %s ***"%(self.package,)
                for entry in self.data:
                    self.s = "CVE: %s\nCVSS Score: %s\nCPE id: %s\nPublished on: \
                    %s\nSummary Description: %s\n"%(entry[0],entry[1],\
                    entry[2],entry[3],entry[4])
                    # can I print the CVSS identifier?
                    # can I print the CVSS identifier in such a way
                    # that it represents a shape?
                    # 
                    # how can I model the attack surface?  What ports does 
                    # this application use?  
                    # What would a malicious attack file look like for this 
                    # cve / security defect?
                    # what does any attack file look like?
                return self.s
        else:
            return self.s

import argparse

# programmer tools

def command_line ():
    """process command line arguments
    Arguments:
    -v --verbosity: verbosity
    positional argument 1: project types
    positional argument 2: project name
    positional argument 3: new project directory
    output: help, useage, and state variables for options on the command line
    """
    DESC = """Checks a list of software programs for known security
    defects documented in the National Vulnerability Database.  Matches the
    project name and version name to CPE vectors in the NVD database.
    """
    import argparse
    parser = argparse.ArgumentParser(description=DESC)
    #parser.add_argument('-c', '--cvss_minimum', help='minimum CVSS score to report', nargs='?', type=float, default=0.0)
    parser.add_argument('-p', '--packagelistfile', help='file where the list of packages to evaluate is stored', nargs='?', default='testlist.txt')
    parser.add_argument('-i', '--items_reported', help='number of items reported for NVD/CVE matches', nargs='?', type=int, default=1)    
    parser.add_argument('-v', '--vfeed_database', help='location of vfeed.db sqlite database from vfeed project', nargs='?', type=str, default='vfeed.db')
    args = parser.parse_args()
    return args

def main ():
    """  read a package inventory file in the form package:version
        check the packages in the NVD database, and report to std out
        depends on vfeed database, package.txt file

    """
    args = command_line()
    # TDB - class does not implement this
    #if args.cvss_minimum:
    #    cvss_minimum = args.cvss_minimum
    if args.packagelistfile:
        print "Using %s as the package list"%(args.packagelistfile)
        packages = packageList(args.packagelistfile)
        packages = packages.getList()
    if args.items_reported:
        i = args.items_reported
    if args.vfeed_database:
        d = args.vfeed_database
    p = checknvd_by_package(package='apache:http_server', database=d, items=20)
    p.get_data()
    print p
    exit()
    # we need to put command line options
    # database
    # age of the CVE's
    # we need to characterize the attack surface, ports program names
    # we need to characterize how to defend against these problems. Besides
    # patching, what else can be done.
    for package in packages:
        print "Checking package text: %s"%(package,)
        try:
            p = checknvd_by_package(package=package, database=d, items=i)
            p.get_data()
            print p
        except KeyboardInterrupt:
            # quit the application
            exit()

if __name__ == "__main__":
    main()
