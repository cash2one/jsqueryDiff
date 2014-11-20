import sys,os

def edit_path(host_info):
	f=open('/home/users/guoan/tools/jsquerydiff/local.conf','r+')
	flist=f.readlines()
	flist[3]='fake_server : ' + host_info + '\n'
	f=open('/home/users/guoan/tools/jsquerydiff/local.conf','w+')
	f.writelines(flist)

if __name__=="__main__":
	edit_path(sys.argv[1])
