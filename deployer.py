import sys
from rdflib import ConjunctiveGraph,Graph
import requests
import json
import logging
import time
logging.basicConfig(filename="sample.log", level=logging.INFO)
reload(sys)  
sys.setdefaultencoding('utf8')

def createGraph(container,iri,g):
	#getting the splug from the iri of the child
	slug = iri.split("/")[-1]
	headers = {"content-type":"rdf/xml","Slug":slug}
	
	#get the graph of the child
        graph = g.get_context(iri)
	data = graph.skolemize().serialize(format="turtle")

	#get the type of the LDPR so that the correct LDP headers can be set
	tquery = "SELECT ?type WHERE { <"+iri+"> <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> ?type .}"
	result = g.query(tquery)
	types = []
	for rtype in result:
		rtype = rtype["type"].replace("http://www.w3.org/ns/ldp#","")
		types.append(rtype)
	if "BasicContainer" in types:
		headers["Link"] = "http://www.w3.org/ns/ldp#BasicContainer" 
	else:
		headers["Link"] = "http://www.w3.org/ns/ldp#Resource"
	headers["Link"] = '<'+headers["Link"]+'>; rel="type"'

	#remove containment and ldp triples
	result = graph.query("PREFIX ldp:<http://www.w3.org/ns/ldp#>  CONSTRUCT { ?s ?p ?o . } WHERE { ?s ?p ?o . FILTER ((?p not in (ldp:contains)) && (?o not in (ldp:BasicContainer)) )}")
	
	#skolemize the graph
	data = Graph().parse(data=result.serialize(format='xml')).skolemize().serialize(format="xml")
	data = data.replace("<"+iri+">","<"+container+"/"+slug+">")
	
	#logging request details
	logging.info("Request Details:")
	logging.info("=================")
	logging.info("Request sent to:"+container)
	logging.info("Request sent with headers:"+str(headers))

	#send the post request
	response = requests.post(container,data=data,headers=headers)
	
	#validate the response
	if "Location" not in response.headers and response.status_code != 201:
		logging.error("LDPR:"+iri+" could not be created")
		print
		print "Request Headers"
		print headers
		
		print
		print "Request data"
		print data
			
		print
		print "Response text"
		print response.text
		print

		sys.exit(0)

       	else:
		containerIRI = response.headers["Location"]
		print containerIRI
		#get all the children (if any) in the LDPR created
		result = graph.query("SELECT ?graph WHERE { ?y <http://www.w3.org/ns/ldp#contains> ?graph .}")
		
		for child in result:
			logging.info("Deploying "+child[0]+" in "+containerIRI)
		       	createGraph(containerIRI,child[0],g)

g = ConjunctiveGraph()
args = {"--base":"","--graph":""}
arg1 = sys.argv[1].split("=")
args[arg1[0]] = arg1[1]

arg2 = sys.argv[2].split("=")
args[arg2[0]] = arg2[1]

base = args["--base"]
ldpDataset = args["--graph"]

logging.info("loading the graph")
g.parse(ldpDataset,format="trig",publicID=base)

#getting all the named graphs from the base
logging.info("Getting all LDPRs from "+base)
graphquery = """SELECT ?graphIRI 
	WHERE { 
		GRAPH <"""+base+"""> { ?s <http://www.w3.org/ns/ldp#contains> ?graphIRI .} 
	}"""
result = qres = g.query(graphquery)
graphNames = []
for gName in result:
	graphNames.append(gName[0])

for graphName in graphNames:
	logging.info("Deploying "+graphName+" in "+base)
	createGraph(base,graphName,g)
