from __future__ import division
import numpy as np
import pandas as pd
from scipy.special import chdtri

def filter_df(df, colname, pred):
	'''
	Filters df down to those rows where pred applied to colname returns True
	
	Parameters
	----------
	df : pd.DataFrame
		Data frame to filter.
	colname : string
		Name of a column in df.
	pred : function
		Function that takes one argument (the data type of colname) and returns True or False.
		
	Returns
	-------
	df2 : pd.DataFrame
		Filtered version of df. 
	
	'''
	if colname in df.columns:
		df2 = df[pred( df[colname] )]
	else: 
		raise ValueError('Cannot find a column named {C}.'.format(C=colname))

	return df2


# input checking functions 

def check_dir(dir):
	'''
	Checks that directions of effect are sensible. Nonsense values should have been caught
	already by coercion to int.
	
	'''
	c1 = dir != 1
	c2 = dir != -1
	if np.any(np.logical_and(c1, c2)):	
		raise ValueError('DIR entry not equal to +/- 1.')


def check_rsid(rsids):
	'''
	Checks that rs numbers are sensible.
	
	'''
	# check for rsid = .
	if np.any(rsids == '.'):
		raise ValueError('Some SNP identifiers are set to . (a dot).')
	
	# check for duplicate rsids
	if np.any(rsids.duplicated('SNP')):
		raise ValueError('Duplicated SNP identifiers.')

	
def check_pvalue(P):
	'''
	Checks that P values are sensible. Nonsense values should have been caught already by 
	coercion to float.
	
	'''
	# check for missing 
	if np.any(np.isnan(P)):
		raise ValueError('Missing P-values')
	
	# check for P outside of the range (0,1]
	if np.max(P) > 1:
		raise ValueError('P-values cannot be > 1.')
	if np.min(P) <= 0:
		raise ValueError('P values cannot be <= 0')


def check_chisq(chisq):
	'''
	Checks that chi-square statistics are sensible. Nonsense values should have been caught
	already by coercion to float.
	
	'''
	if np.any(np.isnan(chisq)):
		raise ValueError('Missing chi-square statistics.')
	
	# check for chisq outside of the range [0,Inf)
	if np.max(chisq) == float('inf'):
		raise ValueError('Infinite chi-square statistics.')
	if np.min(chisq) < 0:
		raise ValueError('Negative chi-square statistics')


def check_maf(maf):
	'''
	Checks that MAFs are sensible. Nonsense values should have been caught already by 
	coercion to float.

	'''
	if np.any(np.isnan(maf)):
		raise ValueError('Missing values in MAF.')
	
	# check for MAF outside of the range (0,1)
	if np.max(maf) >= 1:
		raise ValueError('MAF >= 1.')
	if np.min(maf) <= 0:
		raise ValueError('MAF <= 0.')
	
	
def check_N(N):
	'''
	Checks that sample sizes are sensible. Nonsense values should have been caught already 
	by coercion to int.
	
	'''
	if np.min(N) < 0:
		raise ValueError('Negative N.')


# parsers

def chisq(fh):
	'''
	Parses .chisq files. See docs/file_formats_sumstats.txt
	
	'''
	dtype_dict = {
		'CHR': str,
		'SNP': str,
		'CM': float,
		'BP': int,
		'P': float,
		'CHISQ': float,
		'N': int, # cast to int for typechecking, then switch to float for division
		'MAF': float,
		'INFO': float,
	}
	colnames = open(fh,'rb').readline().split()
	usecols = ['SNP','P','CHISQ','N','MAF','INFO']	
	usecols = [x for x in usecols if x in colnames]
	try:
		x = pd.read_csv(fh, header=0, delim_whitespace=True, usecols=usecols, 
			dtype=dtype_dict)
	except AttributeError as e:
		raise AttributeError('Improperly formatted chisq file: '+ e)

	check_N(x['N'])	
	x['N'] = x['N'].astype(float)
	check_rsid(x['SNP']) 
	
	if 'MAF' in x.columns:
		check_maf(x['MAF'])
		x['MAF'] = np.fmin(x['MAF'], 1-x['MAF'])
	
	if 'P' in x.columns:
		check_pvalue(x['P'])
		x['P'] = chdtri(1, x['P']); 
		x.rename(columns={'P': 'CHISQ'}, inplace=True)
	elif 'CHISQ' in x.columns:
		check_chisq(x['CHISQ'])
	else:
		raise ValueError('.chisq file must have a column labeled either P or CHISQ.')

	return x
	

def betaprod(fh):
	'''
	Parses .betaprod files. See docs/file_formats_sumstats.txt
	
	'''
	dtype_dict = {
		'CHR': str,
		'SNP': str,
		'CM': float,
		'BP': int,
		'P1': float,
		'CHISQ1': float,
		'DIR1': int,
		'N1': int, # cast to int for typechecking, then switch to float later for division
		'P2': float,
		'CHISQ2': float,
		'DIR2': int,
		'N2': int,
		'INFO1': float,
		'INFO2': float,
		'MAF1': float,
		'MAF2': float
	}
	colnames = open(fh,'rb').readline().split()
	usecols = [x+str(i) for i in xrange(1,3) for x in ['DIR','P','CHISQ','N','MAF','INFO']]
	usecols.append('SNP')
	usecols = [x for x in usecols if x in colnames]
	try:
		x = pd.read_csv(fh, header=0, delim_whitespace=True, usecols=usecols, 
			dtype=dtype_dict)
	except AttributeError as e:
		raise AttributeError('Improperly formatted betaprod file: '+ e)
		
	check_rsid(x['SNP'])
	
	for i in ['1','2']:
		N='N'+i; P='P'+i; CHISQ='CHISQ'+i; DIR='DIR'+i; MAF='MAF'+i; INFO='INFO'+i
		BETAHAT='BETAHAT'+i
		check_N(x[N])
		x[N] = x[N].astype(float)
		check_dir(x[DIR])
		if CHISQ in x.columns:
			check_chisq(x[CHISQ])
			betahat = np.sqrt(x[CHISQ]/x[N]) * x[DIR]
			x[CHISQ] = betahat
			x.rename(columns={CHISQ: BETAHAT}, inplace=True)
		elif P in x.columns:
			check_pvalue(x[P])
			betahat = np.sqrt(chdtri(1, x[P])/x[N])	* x[DIR]
			x[P] = betahat
			x.rename(columns={P: BETAHAT}, inplace=True)
		else:
			raise ValueError('No column named P{i} or CHISQ{i} in betaprod.'.format(i=i))

		del x[DIR]
		if MAF in x.columns:
			check_maf(x[MAF])
			x[MAF]  = np.min(x[MAF], 1-x[MAF])
		
	return x

	
def ldscore(fh, num=None):
	'''
	Parses .l2.ldscore files. See docs/file_formats_ld.txt

	If num is not None, parses .l2.ldscore files split across [num] chromosomes (e.g., the 
	output of parallelizing ldsc.py --l2 across chromosomes).

	'''
	parsefunc = lambda y : pd.read_csv(y, header=0, delim_whitespace=True).\
		drop(['CHR','BP','CM','MAF'],axis=1)
	
	if num is not None:
		chr_ld = [parsefunc(fh + str(i) + '.l2.ldscore') for i in xrange(1,num+1)]
		x = pd.concat(chr_ld)
	else:
		x = parsefunc(fh + '.l2.ldscore')
	
	ii = x['SNP'] != '.'
	x = x[ii]
	check_rsid(x['SNP']) 
	x.ix[:,1:len(x.columns)] = x.ix[:,1:len(x.columns)].astype(float)

	return x
	
	
def M(fh, num=None):
	'''
	Parses .l2.M files. See docs/file_formats_ld.txt.
	
	If num is not none, parses .l2.M files split across [num] chromosomes (e.g., the output 
	of parallelizing ldsc.py --l2 across chromosomes).

	'''
	parsefunc = lambda y : [float(z) for z in open(y, 'r').readline().split()]
	if num is not None:
		x = np.sum([parsefunc(fh+str(i)+'.l2.M') for i in xrange(1,num+1)], axis=0)
	else:
		x = parsefunc(fh + '.l2.M')
		
	return x
	

def __ID_List_Factory__(colnames, keepcol, fname_end, header=None, usecols=None):
	
	class IDContainer(object):
		
		def __init__(self, fname):
			self.__usecols__ = usecols
			self.__colnames__ = colnames
			self.__keepcol__ = keepcol
			self.__fname_end__ = fname_end
			self.__header__ = header
			self.__read__(fname)
			if 'SNP' in self.__colnames__:
				check_rsid(self.df['SNP'])
				
			self.n = len(self.IDList)

		def __read__(self, fname):
			end = self.__fname_end__
			if end and not fname.endswith(end):
				raise ValueError('{f} filename must end in {f}'.format(f=end))

			self.df = pd.read_csv(fname, header=self.__header__, usecols=self.__usecols__, 
				delim_whitespace=True)
			if self.__colnames__: self.df.columns = self.__colnames__
			self.IDList = self.df.iloc[:,[self.__keepcol__]]
		
		def loj(self, externalDf):
			'''
			Returns indices of those elements of self.IDList that appear in exernalDf
			'''
			r = externalDf.columns[0]
			l = self.IDList.columns[0]
			merge_df = externalDf.iloc[:,[0]]
			merge_df['keep'] = True
			z = pd.merge(self.IDList, merge_df, how='left',left_on=l, right_on=r, 
				sort=False)
			ii = z['keep'] == True	
			return np.nonzero(ii)[0]

	return IDContainer


PlinkBIMFile = __ID_List_Factory__(['CHR', 'SNP','CM','BP'],1,'.bim',usecols=[0,1,2,3])
VcfSNPFile = __ID_List_Factory__(['CHR','BP','SNP','CM'],2,'.snp',usecols=[0,1,2,3])
PlinkFAMFile = __ID_List_Factory__(['IID'],0,'.fam',usecols=[1])
VcfINDFile = __ID_List_Factory__(['IID'],0,'.ind',usecols=[0])
FilterFile = __ID_List_Factory__(['ID'],0,None,usecols=[0])
AnnotFile = __ID_List_Factory__(None,2,'.annot',header=0,usecols=None)