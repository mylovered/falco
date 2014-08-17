#!/usr/bin/env python
# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4
"""  What are the most risky packages in terms of not being measured by any tool?
dependencies:
    -vfeed database, and a package inventory list
    - software list formatting list being in name or name:version format
      1 package per line, comments start with #

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

import argparse
import time
import re
import sqlite3
TESTLIST = 'testlist.txt'

# enable a simple debug printout function
DEBUG = False

class packageList():
    """ return a generator of list of packages to get tested.
        input: filename where the content is a packagenames
        one per line, comments with # sign
    """
    def __init__ (self, packageFile=TESTLIST):
        """ get a file name when object is instantiated
        """
        self.packageFile = packageFile
        self.packageList = []
    def getList (self):
        """ getList is a generator, it gets the data from the file 
            and yields the data as needed
        """
        try:
            self.packageListInput = open (self.packageFile, 'r').readlines() 
        except Exception, e:
            print "packageList: Exception - %s"%(e,)
            exit(1)
        for each in self.packageListInput:
            # eliminate commented lines
            if re.search(r'^#', each):
                pass
            else:
                # remove newline
                each = each.strip('\n')
                if each != '':
                    self.packageList.append(each)
                    yield each

class checknvd_by_package():
    """ Check a package string for existence in the nvd cpe data
        data string is 'packagename:version'
        depends on the vfeed.db database from the vfeed application
    """
    def __init__ (self, package=None, database='vfeed.db', items=99):
        """ Setup class 
        """
        self.package = package 
        self.database = database
        self.items = items
        self.scanners = 'map_cve_msf map_cve_nessus map_cve_openvas map_cve_saint map_cve_osvdb map_cve_iavm'.split()
        self.riskdict = {}
        self.riskdict['package'] = ''
        self.riskdict['scanner'] = ''
        self.riskdict['cve'] = ''
        self.db_version = None
    def get_data(self):
        """   Get the data from the database.
        """
        if not re.search(":",self.package):
            #print "checknvd_by_package, package has no version info: %s"%(self.package,)
            self.data = None
            return None 
        try:
            """ open the database using Sqlite3, setup a connection
            and establish the SQL cursor
            """
            self.conn = sqlite3.connect(self.database)
            self.cursor = self.conn.cursor()
        except Exception, e:
            print "checknvd_by_package.getdata: %s"%(e,)
            exit()
        # setting up a SQL query for get CPE and CVE data from two tables
        # and match against a package name in the CPE identifiers.
        # match :packagename: or :packagename:n.n.n: packagename
        self.sql = r"""SELECT DISTINCT c.cveid, n.cvss_base, c.cpeid, n.date_published, n.summary
        FROM nvd_db as n
        JOIN cve_cpe as c
        """
        self.sql += r' WHERE c.cveid = n.cveid AND'
        self.sql += r' c.cpeid LIKE "%:' + self.package + r'%"'
        self.sql += r' GROUP BY c.cveid '
        self.sql += r' ORDER BY CAST(n.cvss_base AS REAL) DESC,'
        self.sql += r' n.date_published DESC'
        self.sql += r' LIMIT ' + str(self.items)
        self.sql += r';'
        self.data = self.cursor.execute(self.sql)
        #print self.sql
        # exit
        if self.data != None:
            self.data = self.data.fetchall()
            # note the fetchall gets multitple entries for a given CPE
            # the cpe matching is regex rather than implementing the
            # CPE v1.0 matching, less than or greater than logic.
            self.conn.close()
            return self.data
        else:
            return None
    def get_risk(self):
        self.risklist = []
        if self.data == None:
            return None
        risk_sql = 'select distinct cveid from db_map where cveid = risk_cve is null ;'
        try:
            """ open the database using Sqlite3, setup a connection
            and establish the SQL cursor
            """
            self.conn = sqlite3.connect(self.database)
            self.cursor = self.conn.cursor()
        except Exception, e:
            print "checknvd_by_package.getrisk: %s"%(e,)
            exit()
        # setting up a SQL query for to see for the CVEs we have in self.data, what
        # items are NOT in [map_cve_msf, map_cve_nessus, map_cve_openvas, map_cve_saint, map_cve_osvdb, map_cve_iavm]
        risk_cve_list = []
        for each in self.data:
            risk_cve_list.append(each[0])
        for cve in risk_cve_list:
            for scanner in self.scanners:
                my_risk_sql = risk_sql.replace('db_map',scanner)
                my_risk_sql = my_risk_sql.replace('risk_cve',r'"' + cve + r'"')
                l = self.cursor.execute(my_risk_sql)
                self.risklist = l.fetchall()
                #print type(self.riskdict), self.risklist, scanner, self.package
                self.riskdict['package'] += str(self.package)
                self.riskdict['scanner'] += str(scanner)
                self.riskdict['cve'] += str(self.risklist)
        self.conn.close()
        return self.riskdict           
    def __len__(self):
        """ enable len operations on this object's data
        """
        if self.data:
            return len(self.data)
        else: 
            return 0
    def db_ver(self):
        """ return the db_version
        """
        if self.db_version == None:
            try:
                self.conn = sqlite3.connect(self.database)
                self.cursor = self.conn.cursor()
                self.db_version = self.cursor.execute(r'select db_version from stat_vfeed_kpi;')
                self.db_version = self.db_version.fetchall()
                self.db_version = self.db_version[0]
                # note the fetchall gets multitple entries for a given CPE
                # the cpe matching is regex rather than implementing the
                # CPE v1.0 matching, less than or greater than logic.
                self.conn.close()           
            except Exception, e:
                print "checknvd_by_package.db_ver: %s"%(e,)
                exit()
            return self.db_version[0]
        else:
            return self.db_version[0]
    def __str__(self):
        """ implement string output for object, embedded formatting and 
        labeling for the data.
        """
        # accumulate all of the string data in s
        self.s = ''
        if len(self.data) > 0:
                self.s = ''
                # accumulate CVE identifiers in cvelist, so that we don't repeat informing
                # about a CVE in the s string, this accumulation may be dead code, since 
                # the SQL seems to eliminate duplicates
                # 
                self.cvelist = []
                for entry in self.data:
                    if entry[0] not in self.cvelist:
                        self.s += "\t\t*** Potential security defect found in %s\n"%(self.package,)
                        self.s += "CVE: %s\nCVSS Score: %s\nCPE id: %s\nPublished on: \
%s\nSummary Description: %s\n\n"%(entry[0],entry[1],\
                        entry[2],entry[3],entry[4])
                        # record the CVE and don't report it again in the string output
                        self.cvelist.append(entry[0])
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
    def __repr__ (self):
        """ implement the string representation of the object
        """
        return __str__()

def command_line():
    """process command line arguments
    Arguments: --debug, --packagelistfile --items_reported, --vfeed_database
    output: help, usage, and state variables for options on the command line
    """

    DESC = """Checks a file list of software programs for known security
    defects documented in the National Vulnerability Database.  Matches the
    project name and version name to CPE vectors in the NVD database.
    """
    parser = argparse.ArgumentParser(description=DESC)
    #parser.add_argument('-c', '--cvss_minimum', help='minimum CVSS score to report', nargs='?', type=float, default=0.0)
    parser.add_argument('--debug', help='turn on debug output', action = 'store_true')
    parser.add_argument('-p', '--packagelistfile', help='file where the list of packages to evaluate is stored', nargs='?', default=TESTLIST)
    parser.add_argument('-i', '--items_reported', help='number of items reported for NVD/CVE matches', nargs='?', type=int, default=1)    
    parser.add_argument('-v', '--vfeed_database', help='location of vfeed.db sqlite database from vfeed project', nargs='?', type=str, default='vfeed.db')
    args = parser.parse_args()
    return args

def db_print (DEBUG, m='module', s='string'):
    """ debug print:
    print what module, and then what string output
    doh, why use this when python has logging?
    """
    if DEBUG == True:
        print "debug: module %s, \ndebug message: %s"%(m,s)

def detailed_vuln_report(vuln_data={}):
    """ print a detailed vulnerability report 
    based on the collected vulnerability data

    input: a dictionary of vulnerability information
    output: print to std out
    """
    s = ''
    for each in vuln_data.keys():
        entry = vuln_data[each]
        for cve in entry:
            s += "\t\t*** Potential security defect found in %s\n"%(each,)
            s += "CVE: %s\nCVSS Score: %s\nCPE id: %s\nPublished on: \
            %s\nSummary Description: %s\n\n"%(cve[0],cve[1],\
            cve[2],cve[3],cve[4])  
    print s

def main():
    """  read a package inventory file in the form package:version
        check the packages in the NVD database, and report to std out
        depends on vfeed database, package.txt file

    """
    args = command_line()
    if args.debug:
        DEBUG = True
    else:
        DEBUG = False
    if args.packagelistfile:
        print "\tReport generated using %s as the package list."%(args.packagelistfile)
        packages = packageList(args.packagelistfile)
        packages = packages.getList()
    else:
        packages = packageList(TESTLIST)
        packages = packages.getList()        
    if args.items_reported:
        i = args.items_reported
    if args.vfeed_database:
        d = args.vfeed_database
    # we need to put command line options
    # age of the CVE's
    # we need to characterize the attack surface, ports program names
    # we need to characterize how to defend against these problems. Besides
    # patching, what else can be done.
    # variables used for reporting
    not_found = ''
    not_found_c = 0
    found = ''
    found_c = 0
    detailed_report = {}
    risks = []
    for package in packages:
        try:
            p = checknvd_by_package(package=package, database=d, items=i)
            report = p.get_data()
            risks.append(p.get_risk())
            if len(p) > 0:
                found += "Package text: " + package + " found.\n"
                found_c += 1
                #db_print (DEBUG,m='main, packagelistfile',s=package)
                #print p
                detailed_report[package]=report
            else:
                not_found_c += 1
                not_found += "Package text: " + package + " not found.\n"
        except KeyboardInterrupt:
            # if the user is impatient, report some output
            db_version = p.db_ver()
            print "Version of vfeed database used in this report was %s, and the"%(db_version,),
            print "report was run on %s."%(time.strftime("%d/%m/%Y at %H:%M:%S"),)
            print "The report was interuppted with control-c"
            # print partial summary
            print "\tThis is a PARTIAL report of findings:"
            print "These %s packages were found in the NVD database and reported above:"%(found_c,)
            print found 
            print "These %s packages were not found in the NVD database:"%(not_found_c,)
            print not_found
            print "PARTIAL findings as follows:"
            detailed_vuln_report (detailed_report)
            # quit the application
            exit(1)
    # print summary
    print "\tReport of possible vulnerability findings, for %s packages requested:"%(found_c + not_found_c,)
    print "These %s packages were found with vulnerability in the NVD database and reported above:"%(found_c,)
    print found 
    print "These %s packages were not found in the NVD database:"%(not_found_c,)
    print not_found
    print "Detailed findings as follows:"
    detailed_vuln_report (detailed_report)
    print "The following CVE/products were mapped into various tools:\n %s"%(risks[0],)
    db_version = p.db_ver()
    print "Version of vfeed database used in this report was %s\nThe"%(db_version,),
    print "report was run on %s."%(time.strftime("%d/%m/%Y at %H:%M:%S"),)
    exit(0)
if __name__ == "__main__":
    main()
