import sys
from rdflib import ConjunctiveGraph,Graph
import requests
import json

base = "http://ci.emse.fr/marmotta/ldp/test12/"

def createGraph(container,iri,g):
	slug = iri.split("/")[-1]
	headers = {"content-type":"text/turtle","Slug":slug}
        graph = g.get_context(iri)
	data = graph.skolemize().serialize(format="turtle")
	tquery = "SELECT ?type WHERE { <"+iri+"> <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> ?type .}"
	result = g.query(tquery)
	for rtype in result:
		rtype = str(rtype[0])
		if rtype == "http://www.w3.org/ns/ldp#BasicContainer":
			headers["Link"] = rtype
		else:
			headers["Link"] = "http://www.w3.org/ns/ldp#Resource"
	headers["Link"] = "<"+headers["Link"]+'>; rel="type"'
	
	#remove containment and ldp triples
	result = graph.query("PREFIX ldp:<http://www.w3.org/ns/ldp#>  CONSTRUCT { ?s ?p ?o . } WHERE { ?s ?p ?o . FILTER ((?p not in (ldp:contains)) && (?o not in (ldp:BasicContainer)) )}")

	data = Graph().parse(data=result.serialize(format='xml')).skolemize().serialize(format="turtle")
	response = requests.post(container,data=data,headers=headers)
        result = graph.query("SELECT ?graph WHERE { ?y <http://www.w3.org/ns/ldp#contains> ?graph .}")
	if "Location" not in response.headers:
		print headers
		print data
		print response.text
        for child in result:
                createGraph(response.headers["Location"],child[0],g)

g = ConjunctiveGraph()
ldpDataset = sys.argv[1]
g.parse(ldpDataset,format="trig",publicID=base)

#getting all the named graphs
graphquery = """SELECT ?graphIRI 
	WHERE { 
		GRAPH <"""+base+"""> { ?s <http://www.w3.org/ns/ldp#contains> ?graphIRI .} 
	}"""
result = qres = g.query(graphquery)
graphNames = []
for gName in result:
	graphNames.append(gName[0])

for graphName in graphNames:
	createGraph(base,graphName,g)
