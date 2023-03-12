import sys, optparse, os
sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)) + '/../../tests/accuracyTest/')
import audioDB as db


def buildID(build_name):
	c = db.conn.cursor()
	c.execute(
	'''SELECT cdash.build.id
	   FROM cdash.build
	   WHERE cdash.build.name = %s
	   order by cdash.build.id DESC
	   limit 1
	''', (build_name))
	return c.fetchone()[0]


def accuracy(build_name):
	c = db.conn.cursor()
	c.execute(
	'''SELECT
	       correct-insertions         as accuracy,
	       (correct-insertions)/total as accuracy_pct,
	       substitutions/total        as substitutions_pct,
	       deletions/total            as deletions_pct,
	       insertions/total           as insertions_pct,
	       correct/total              as correct_pct,
	       totalerror/total           as totalerror_pct
	   FROM
	       (SELECT
	           sum(Audio.HypothesisItems.status='correct')      as correct,
	           sum(Audio.HypothesisItems.status='substitution') as substitutions,
	           sum(Audio.HypothesisItems.status='deletion')     as deletions,
	           sum(Audio.HypothesisItems.status='insertion')    as insertions,
	           sum(Audio.HypothesisItems.status!='insertion')   as total,
	           sum(Audio.HypothesisItems.status!='correct')     as totalerror,
	           build.id as 'build.id'
	       FROM
	           cdash.test
	           INNER JOIN cdash.testaccuracy    ON testaccuracy.testid=test.id
	           INNER JOIN Audio.TestGroups      ON Audio.TestGroups.id = testaccuracy.testgroupid
	           INNER JOIN Audio.Tests           ON Audio.Tests.testgroupid = Audio.TestGroups.id
	           INNER JOIN Audio.HypothesisItems ON Audio.HypothesisItems.id = Audio.Tests.hypothesisid
	           INNER JOIN cdash.build2test      on build2test.testid = test.id
	           INNER join cdash.build           on build.id = build2test.buildid
	       WHERE
	           build2test.buildid = %s
	       group by build.id ) as t1
	''', (buildID(build_name)))
	return c.fetchone()[1]


def main():
	parser = optparse.OptionParser()
	
	# add options to the option parser
	parser.add_option('-b', '--build-name',
	                  help   = 'The build name to use for database queries.')
	parser.add_option('-i', '--build-id',
	                  action = 'store_true',
	                  help   = 'Print the build id for the specified build name.')
	parser.add_option('-a', '--accuracy',
	                  action = 'store_true',
	                  help   = 'Print the accuracy results for the specified build name.')
	
	# set defaults and parse options, arguments
	parser.set_defaults(build_name = None,
	                    build_id   = None,
	                    accuracy   = None)
	options, args = parser.parse_args()
	
	
	if not options.build_name:
		print 'Must specify build name.'
		exit(1)
	if options.build_id:
		print str(buildID(options.build_name))
	if options.accuracy:
		print str(accuracy(options.build_name))


if __name__ == '__main__':
	main()
