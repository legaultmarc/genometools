
import re
import urllib2
import contextlib
import json

import settings

__all__ = ["SNP", ]

class SNP(object):
    def __init__(self, *args, **kwargs):
        """Initialize a SNP. 

        This can be done in two ways: either by providing ordered fields: 
        ``chrom, pos, rs, ref, alt`` or by using named parameters.

        """

        parameters = [
            "chrom", 
            "pos",
            "rs",
            "ref",
            "alt",
        ]

        if len(args) == 5:
            # Initialize assuming (chrom, pos, rs, ref, alt)
            for i, p in enumerate(parameters):
                setattr(self, p, args[i])
        else:
            for k in kwargs.keys():
                if k not in parameters:
                    raise Exception("Unknown parameter {}.".format(k))

                setattr(self, k, kwargs.pop(k))

        # Normalize attributes.
        for p in parameters:
            if getattr(self, p, "-1") == "-1":
                raise Exception("Missing parameter {}.".format(p))

        self.pos = int(self.pos)
        assert re.match(r"([0-9]{1,2}|MT|X|Y)", str(self.chrom))
        assert self.rs is None or re.match(r"^rs[0-9]+$", self.rs)
        assert type(self.ref) is str and len(self.ref) == 1
        assert type(self.alt) is str and len(self.alt) == 1

    def get_position(self):
        """Returns a variant in the standard chrXX:pos notation. """
        return "chr{}:{}".format(self.chrom, self.pos)

    def vcf_header(self):
        """Returns a valid VCF header line. """
        return "\t".join([
            "#CHROM",
            "POS",
            "ID",
            "REF",
            "ALT",
            "QUAL",
            "FILTER",
            "INFO",
        ])

    def vcf_line(self):
        """Returns a line describing the current variant as expected by the VCF format. 

        """
        return "\t".join(str(i) for i in [
            self.chrom,
            self.pos,
            self.rs if self.rs else ".",
            self.ref,
            self.alt,
            ".", # No Quality
            "PASS", # PASS for filter
            ".", # Info
        ])

    @classmethod
    def from_ensembl_api(cls, rs, build=settings.BUILD):
        """Gets the information from the Ensembl REST API.

        :param rs: The rs number for the variant of interest.
        :param build: The genome build (e.g. GRCh37 or GRCh38).

        """
        if build == "GRCh37":
            url = ("http://grch37.rest.ensembl.org/variation/homo_sapiens/{snp}"
                   "?content-type=application/json")
        elif build == "GRCh38":
            url = ("http://rest.ensembl.org/variation/homo_sapiens/{snp}"
                   "?content-type=application/json")
        else:
            raise Exception("Unknown build '{}'.".format(build))

        url = url.format(snp=rs)
        try:
            with contextlib.closing(urllib2.urlopen(url)) as stream:
                response = json.load(stream)
        except urllib2.HTTPError:
            print "Request '{}' failed.".format(url)
            return None

        pos = None
        for mapping in response["mappings"]:
            if mapping["assembly_name"] == build:
                pos = "chr{}_{}".format(
                    mapping["location"].split("-")[0], mapping["allele_string"]
                )

        if not pos:
            raise Exception("Could not find all the information to create SNP "
                "object from Ensembl.")

        return SNP.from_str(pos, rs=rs)


    @classmethod
    def from_str(cls, s, rs=None):
        """Parses a variant object from a str of the form chrXX:YYYY_R/A. 
        
        :param s: The string to parse the SNP from (Format: chrXX:YYY_R/A).
        :param rs: An optional parameter specifying the rs number.

        :returns: A SNP object.

        """
        s = s.lstrip("chr")
        chrom, s = s.split(":")
        pos, s = s.split("_")
        ref, alt = s.split("/")
        return SNP(chrom, pos, rs, ref, alt)

    def __repr__(self):
        return "chr{}:{}_{}/{}".format(self.chrom, self.pos, self.ref, self.alt)

