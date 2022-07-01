import random
import threading
from metatutu.pipeline import *
from metatutu.debugging import *

"""
Pipeline for building product X.

Product X is a customized product with 2 parts (part A and part B).
Both parts are customized as well, says they are built based on
customer's demand.  Final product is a package with it's unique part A
and part B.

It will organize a pipeline with below roles:
- Dispatcher: who watch the job queue and assign tasks for new jobs
- Part A Team: who will build part A
- Part B Team: who will build part B
- Collector: who watch the job queue and assign tasks for jobs with both parts ready
- Pack Team: who will pack part A and part B together and deliver

Job state:
- s0(init): new job
- s1(building): task of building parts had been assigned
- s2(packing): both parts had been built, being packed
- s3(delivered): product had been delivered
"""

class Dispatcher(Controller):
	def __init__(self):
		Controller.__init__(self)
		self.pipeline = None

	def _process(self):
		while True:
			#dispatch tasks of part A and part B for new jobs
			for job in self.pipeline.job_queue:
				if job.state == ProductXPipelineJob.s0_init:
					#update job state
					job.state = ProductXPipelineJob.s1_building

					#assign task for part A
					task_part_a = {
						"job": job
					}
					self.pipeline.part_a_team.task_queue.push_task(task_part_a)

					#assign task for part B
					task_part_b = {
						"job": job
					}
					self.pipeline.part_b_team.task_queue.push_task(task_part_b)

					#log
					print("dispatcher: dispatched {0}".format(job.id))
	
			#check stop request
			if self._dismissNotice.is_set(): break

			#sleep
			time.sleep(0.000001)

class PartAOperator(Operator):
	def __init__(self):
		Operator.__init__(self)
		self.team = None
		self.task_queue = None

	def _process_task(self, task):
		job = task["job"]
		
		#build part A
		job.part_a = "part A for " + job.id

		#sign
		job.part_a_operator = self.id

		#log
		print("part A operator ({0}): built {1}".format(self.id, job.id))

		#simulate length of process
		time.sleep(0.1)

	def _pop_task(self):
		if self.task_queue is None: return None
		return self.task_queue.pop_task(0.000001)

	def bind(self, data):
		self.team = data
		self.task_queue = data.task_queue

class PartATeam(Team):
	def __init__(self):
		Team.__init__(self)
		self.operator_class = PartAOperator
	
	def __del__(self):
		Team.__del__(self)

	def hire(self):
		#create task queue
		self.task_queue = TaskQueue()

		#hire operators
		self.hire_operator(5)
	
	def dismiss(self):
		#finish all tasks
		self.finish_all_tasks()

		#dismiss operators
		self.operators.dismiss_all()

class PartBOperator(Operator):
	def __init__(self):
		Operator.__init__(self)
		self.team = None
		self.task_queue = None

	def _process_task(self, task):
		job = task["job"]

		#build part B
		job.part_b = "part B for " + job.id

		#sign
		job.part_b_operator = self.id

		#log
		print("part B operator ({0}): built {1}".format(self.id, job.id))

		#simulate length of process
		time.sleep(0.1)

	def _pop_task(self):
		if self.task_queue is None: return None
		return self.task_queue.pop_task(0.000001)

	def bind(self, data):
		self.team = data
		self.task_queue = data.task_queue

class PartBTeam(Team):
	def __init__(self):
		Team.__init__(self)
		self.operator_class = PartBOperator
	
	def __del__(self):
		Team.__del__(self)

	def hire(self):
		#create task queue
		self.task_queue = TaskQueue()

		#hire operators
		self.hire_operator(5)
	
	def dismiss(self):
		#finish all tasks
		self.finish_all_tasks()

		#dismiss operators
		self.operators.dismiss_all()

class Collector(Controller):
	def __init__(self):
		Controller.__init__(self)
		self.pipeline = None

	def _process(self):
		while True:
			#dispatch tasks of packing for jobs with part A and part B built
			for job in self.pipeline.job_queue:
				if job.state == ProductXPipelineJob.s1_building:
					if (job.part_a is not None) and (job.part_b is not None): 
						#update job state
						job.state = ProductXPipelineJob.s2_packing

						#assign task for packing
						task_pack = {
							"job": job
						}
						self.pipeline.pack_team.task_queue.push_task(task_pack)

						#log
						print("collector: dispatched {0}".format(job.id))

			#check stop request
			if self._dismissNotice.is_set(): break

			#sleep
			#time.sleep(0.000001)

class PackOperator(Operator):
	def __init__(self):
		Operator.__init__(self)
		self.team = None
		self.task_queue = None

	def _process_task(self, task):
		job = task["job"]

		#sign
		job.pack_operator = self.id

		#deliver product
		msg = "pack operator ({0}): delivering {1}\r\n".format(job.pack_operator, job.id)
		msg += "    {0} by {1}\r\n".format(job.part_a, job.part_a_operator)
		msg += "    {0} by {1}".format(job.part_b, job.part_b_operator)
		print(msg)

		#update job state
		job.state = ProductXPipelineJob.s3_delivered

		#simulate length of process
		time.sleep(0.1)

	def _pop_task(self):
		if self.task_queue is None: return None
		return self.task_queue.pop_task(0.00001)

	def bind(self, data):
		self.team = data
		self.task_queue = data.task_queue

class PackTeam(Team):
	def __init__(self):
		Team.__init__(self)
		self.operator_class = PackOperator
	
	def __del__(self):
		Team.__del__(self)

	def hire(self):
		#create task queue
		self.task_queue = TaskQueue()

		#hire operators
		self.hire_operator(5)
	
	def dismiss(self):
		#finish all tasks
		self.finish_all_tasks()

		#dismiss operators
		self.operators.dismiss_all()

class ProductXPipelineJob:
	s0_init = 0
	s1_building = 1
	s2_packing = 2
	s3_delivered = 3

	def __init__(self):
		self.lock = threading.Lock()
		self.state = ProductXPipelineJob.s0_init
		self.id = None
		self.part_a = None
		self.part_a_operator = None
		self.part_b = None
		self.part_b_operator = None
		self.pack_operator = None

class ProductXPipeline(Pipeline):
	def __init__(self):
		Pipeline.__init__(self)
		self.logger = None
		self.job_queue = []
		self.dispatcher = Dispatcher()
		self.part_a_team = PartATeam()
		self.part_b_team = PartBTeam()
		self.collector = Collector()
		self.pack_team = PackTeam()

	def __del__(self):
		Pipeline.__del__(self)

	def hire(self):
		#hire teams
		self.part_a_team.hire()
		self.part_b_team.hire()
		self.pack_team.hire()

		#hire collector
		self.collector.pipeline = self
		self.collector.hire()

		#hire dispatcher
		#NOTICE: since dispatcher is the first step in pipeline, make sure
		#it will be hired after rest pipeline had been ready.
		self.dispatcher.pipeline = self
		self.dispatcher.hire()

	def dismiss(self):
		#dismiss dispatcher
		self.dispatcher.dismiss()

		#dismiss collector
		self.collector.dismiss()

		#dismiss teams
		self.pack_team.dismiss()
		self.part_a_team.dismiss()
		self.part_b_team.dismiss()

	def finish_all_jobs(self):
		#NOTICE: This is just an example with a static job queue.  In real
		#applications, typically, the job queue is dynamic, so should not use
		#below logic to check the job queue.  Also, make sure job queue access
		#will be thread safe.
		while True:
			in_process_job = None
			for job in self.job_queue:
				if job.state != ProductXPipelineJob.s3_delivered:
					in_process_job = job
					break
			if in_process_job == None: break

if __name__ == "__main__":
	clocker = Clocker()

	#hire pipeline
	clocker.reset()
	pipeline = ProductXPipeline()
	for i in range(0, 50):
		job = ProductXPipelineJob()
		job.id = "job {0}".format(i + 1)
		pipeline.job_queue.append(job)
	pipeline.hire()
	clocker.record("hire")

	#wait
	pipeline.finish_all_jobs()
	clocker.record("wait")
	
	#dismiss
	pipeline.dismiss()
	clocker.record("dismiss")

	#show result
	print(clocker.results_text())
